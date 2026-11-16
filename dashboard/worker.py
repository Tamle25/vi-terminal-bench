"""Fixed dashboard actions; actual model calls stay inside the frozen CLI gates."""
import argparse
from contextlib import closing, redirect_stdout
import io
import json
from pathlib import Path
import re
import sqlite3
import sys
import threading
import time
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from scoped_credentials import sanitize
from dashboard.runtime_clock import stable_runtime_clock, POLICY as CLOCK_POLICY
from dashboard.recovery import prepare_unsubmitted_resume

OUTPUT = sys.stdout
OUTPUT_LOCK = threading.Lock()


def event(kind, **values):
    with OUTPUT_LOCK:
        OUTPUT.write('@@DASHBOARD ' + json.dumps(sanitize({'type': kind, **values}), ensure_ascii=False) + '\n'); OUTPUT.flush()


def preview():
    cfg = json.loads((ROOT / 'configs/development-benchmark.json').read_text(encoding='utf-8'))
    from development_contracts import planned
    plan = planned(ROOT, cfg, 'development-batch', 'dashboard-preview')
    event('message', message='Preview đạt: 6 task × EN/VI × 3 repeat = 36 lượt. Không đọc key, không gọi API.')
    event('runtime', runtime={'preview_passed': len(plan['planned_trials']) == 36, 'provider_calls': 0,
                             'model': cfg['model'], 'planned_trials': len(plan['planned_trials']),
                             'credential_read': False})
    if len(plan['planned_trials']) != 36:
        raise ValueError('TASK_COUNT_DRIFT')


def pick_validation(dev, cfg):
    root = Path(cfg['state_root'])
    candidates = sorted(root.glob('validation-*/validation.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    candidates += sorted(root.glob('dashboard-validation-*/validation.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in candidates:
        try:
            dev.validation_for(cfg, path)
            return path
        except (ValueError, OSError, KeyError):
            continue
    event('message', message='Đang kiểm backend: build image, oracle và no-op cho 6 tác vụ. Không gọi model.')
    output = root / ('dashboard-validation-' + uuid.uuid4().hex[:12])
    dev.validate_containers(cfg, output)
    return output / 'validation.json'


def pick_smoke(dev, cfg):
    paths = sorted((Path(cfg['state_root']) / 'runs').glob('*/report-*/summary.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in paths:
        try:
            dev.smoke_for(cfg, path)
            return path
        except (ValueError, OSError, KeyError, sqlite3.Error):
            continue
    raise ValueError('MATCHING_MODEL_SMOKE_REQUIRED')


def readonly_bundle(dev, cfg, plan):
    root = Path(cfg['state_root']); runroot = root / 'runs' / plan['run_id']
    with closing(sqlite3.connect((root / 'ledger.sqlite3').resolve().as_uri() + '?mode=ro', uri=True)) as db:
        record = db.execute('SELECT contract FROM runs WHERE id=?', (plan['run_id'],)).fetchone()
        if not record or record[0] != dev.digest(plan):
            raise ValueError('REPORT_RUN_CONTRACT_DRIFT')
        rows = {tid: json.loads(text) for tid, text, sha in db.execute('SELECT trial,record,sha FROM development_outcomes WHERE run=?', (plan['run_id'],)) if dev.digest(json.loads(text)) == sha}
    folder = runroot / ('report-dashboard-' + uuid.uuid4().hex[:12])
    summary = dev.report(plan, runroot, folder, ledger_state=readonly_ledger(cfg), authoritative=rows)
    event('bundle', summary=summary, trials=[rows[t['trial_id']] for t in plan['planned_trials'] if t['trial_id'] in rows])


def readonly_ledger(cfg):
    # Reuse the ledger's accounting algorithm on a read-only connection. Skip its
    # constructor intentionally: it contains DDL and mutable initialization.
    from development_ledger import DevelopmentLedger, POLICY
    with closing(sqlite3.connect((Path(cfg['state_root']) / 'ledger.sqlite3').resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        if tuple(db.execute('SELECT account,cap,origin FROM identity WHERE id=1').fetchone()) != (cfg['account_reference'], dev_nano(cfg['pool_cap_usd']), 'real'):
            raise ValueError('LEDGER_IDENTITY_DRIFT')
        if db.execute('SELECT policy FROM development_policy WHERE id=1').fetchone()[0] != POLICY:
            raise ValueError('SETTLEMENT_POLICY_DRIFT')
        ledger = object.__new__(DevelopmentLedger); ledger.db = db
        return ledger.inspect()


def dev_nano(value):
    from usd_ledger_v1 import nano
    return nano(value)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['preview', 'check', 'smoke', 'batch', 'report', 'resume', 'status'])
    parser.add_argument('--run-id', required=True); parser.add_argument('--target-run-id')
    args = parser.parse_args()
    for value in [args.run_id, args.target_run_id]:
        if value is not None and not re.fullmatch(r'dashboard-(?:smoke|batch|preview|check|report|status|resume)-[a-f0-9]{12}', value):
            raise ValueError('RUN_ID_DENIED')
    if args.action == 'preview':
        return preview()
    if sys.platform != 'linux':
        raise ValueError('LINUX_RUNTIME_REQUIRED')
    import dev_benchmark as dev
    cfgpath = ROOT / 'configs/development-benchmark.json'; cfg = dev.load(cfgpath); dev.validate_config(cfg)
    event('ledger', ledger=readonly_ledger(cfg))
    with stable_runtime_clock(dev) as clock:
        execute_action(args, dev, cfgpath, cfg, clock)


def execute_action(args, dev, cfgpath, cfg, clock):
    if args.action == 'status':
        event('message', message='Đã đồng bộ ngân sách từ ledger Linux ở chế độ chỉ đọc. Không đọc key hoặc gọi API.')
        return
    if args.action == 'report':
        plan = dev.load(Path(cfg['state_root']) / 'stage11-batch-plan.json')
        readonly_bundle(dev, cfg, plan)
        event('message', message='Đã dựng lại baseline từ ledger và outcome Linux. Không đọc key hoặc gọi model.')
        return
    if args.action == 'resume':
        if not args.target_run_id:
            raise ValueError('RESUME_TARGET_REQUIRED')
        planpath = Path(cfg['state_root']) / (args.target_run_id + '.json')
        recovered = prepare_unsubmitted_resume(ROOT, planpath)
        if recovered:
            event('message', message='Archived proven pre-loop failures; retained completed trials. No provider request was retried.')
    else:
        proof = pick_validation(dev, cfg)
        if args.action == 'check':
            dev.image_check(dev.validation_for(cfg, proof)['images'])
            event('runtime', runtime={'validation_passed': True, 'tasks': 6, 'oracle_pass': 6, 'nop_fail': 6,
                                      'provider_calls': 0, 'credential_read': False})
            event('message', message='Backend sẵn sàng: 6 oracle đạt, 6 no-op thất bại đúng kỳ vọng. Không gọi model.')
            return
        scope = 'development-smoke' if args.action == 'smoke' else 'development-batch'
        smoke = pick_smoke(dev, cfg) if args.action == 'batch' else None
        planpath = Path(cfg['state_root']) / (args.run_id + '.json')
        dev.freeze_plan(cfg, scope, args.run_id, proof, planpath, smoke)
    plan = dev.load(planpath)
    # execute() owns creation of runs/<id>; never pre-create it for a new run.
    revisions = Path(cfg['state_root']) / 'runtime-revisions' / plan['run_id']
    revisions.mkdir(parents=True, exist_ok=True)
    revision = {'schema':'vi-dashboard-runtime-revision/1', 'run_id':plan['run_id'],
                'frozen_plan_sha256':dev.file_digest(planpath), 'frozen_harness_sources':plan['source_sha256'],
                'runtime_clock':clock.receipt(),
                'controller_extension_sha256':{name:dev.file_digest(ROOT/name) for name in
                    ['dashboard/worker.py','dashboard/runtime_clock.py','dashboard/recovery.py']},
                'model_prompt_task_limits_unchanged':True, 'original_core_source_freeze_unchanged':True}
    revision_id = 'clock-' + uuid.uuid4().hex[:12]
    archive = revisions / (revision_id + '.source.zip')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, expected in revision['controller_extension_sha256'].items():
            if dev.file_digest(ROOT/name) != expected:
                raise ValueError('CONTROLLER_EXTENSION_SOURCE_DRIFT')
            bundle.write(ROOT/name, name)
    revision['controller_extension_archive'] = str(archive)
    revision['controller_extension_archive_sha256'] = dev.file_digest(archive)
    dev.write_new(revisions / (revision_id + '.json'), revision)
    event('runtime_policy', runtime_policy=revision)
    event('message', message='Đang chạy ' + str(len(plan['planned_trials'])) + ' lượt độc lập; kết quả và chi phí được ghi vào ledger.')
    stop = threading.Event()
    def progress():
        # Show only authoritative, committed outcomes. Partial work never becomes a pass.
        while not stop.wait(2):
            try:
                with closing(sqlite3.connect((Path(cfg['state_root']) / 'ledger.sqlite3').resolve().as_uri() + '?mode=ro', uri=True)) as db:
                    rows = [json.loads(text) for tid,text,sha in db.execute('SELECT trial,record,sha FROM development_outcomes WHERE run=?', (plan['run_id'],)) if tid in {t['trial_id'] for t in plan['planned_trials']} and dev.digest(json.loads(text)) == sha]
                event('progress', progress={'finished': len(rows), 'total': len(plan['planned_trials']),
                                           'passed': sum(r.get('reward') == 1 for r in rows), 'trials': rows})
            except (sqlite3.Error, ValueError, OSError):
                pass
    watcher = threading.Thread(target=progress, daemon=True); watcher.start()
    try:
        result = dev.execute(cfg, cfgpath, planpath, resume=args.action == 'resume')
    finally:
        stop.set(); watcher.join(3)
        try:
            event('ledger', ledger=readonly_ledger(cfg))
        except (OSError, ValueError, sqlite3.Error):
            pass
    # Preserve ledger exposure from execute; report-only exports do not invent it.
    runroot = Path(cfg['state_root']) / 'runs' / plan['run_id']
    trials = [dev.load(runroot / t['trial_id'] / 'outcome.json') for t in plan['planned_trials'] if (runroot / t['trial_id'] / 'outcome.json').exists()]
    event('bundle', summary=result, trials=trials)
    if not result['complete'] or (plan['scope'] == 'development-smoke' and not result['technical_smoke_passed']):
        raise SystemExit(3)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        code = exc.args[0] if isinstance(exc, ValueError) and exc.args and re.fullmatch(r'[A-Z_]{1,150}', str(exc.args[0])) else 'RUNTIME_UNAVAILABLE'
        event('error', code=code, message='Lần chạy đã dừng: ' + code + '. Kiểm tra Docker/WSL và nhật ký; không tự gửi lại request chưa rõ trạng thái.')
        raise SystemExit(2) from None
