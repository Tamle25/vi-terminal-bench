"""Archive ONLY a failed pre-loop trial with zero request/tool intents.

Preserves the frozen run contract, all raw failure evidence and every billed row.
No provider calls, invoices, holds, uncertain receipts or model answers are reset.
"""
from contextlib import closing
import datetime as dt
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def eligible(requests, tools, row, folder):
    if requests or tools or row.get('status') != 'infra_error' or row.get('valid') is not False:
        raise ValueError('PRE_LOOP_ZERO_INTENTS_REQUIRED')
    if (row.get('error_code') != 'GATE_DENIED_ATTESTATION_EXPIRED_OR_INVALID'
            or row.get('raw_loop') is not None or row.get('raw_verifier') is not None
            or row.get('request_ids') != [] or row.get('input_tokens') != 0 or row.get('output_tokens') != 0
            or row.get('cleanup') != 'removed_owned_container'):
        raise ValueError('PRE_LOOP_FAILURE_PROOF_REQUIRED')
    if {p.name for p in folder.iterdir()} != {'outcome.json', 'runtime-attestation.json'}:
        raise ValueError('UNEXPECTED_TRIAL_EVIDENCE')


def archive_preloop_failure(repo, plan_path, trial_id):
    import development_contracts
    repo, plan_path = Path(repo), Path(plan_path)
    plan = json.loads(plan_path.read_text(encoding='utf-8')); root = Path(plan['config']['state_root']).resolve()
    run = plan['run_id']; runroot = root / 'runs' / run; folder = runroot / trial_id
    if (plan['scope'] not in development_contracts.SCOPES
            or trial_id not in {t['trial_id'] for t in plan['planned_trials']}
            or development_contracts.sources(repo) != plan['source_sha256']):
        raise ValueError('FROZEN_EXECUTION_SOURCE_OR_TRIAL_DRIFT')
    if (not folder.resolve().is_relative_to(runroot) or any(p.is_symlink() for p in [folder, *folder.parents])):
        raise ValueError('RECOVERY_PATH_POLICY')
    alias = trial_id + '--preloop-blocked-' + uuid.uuid4().hex[:8]
    destination = runroot / 'blocked-trials' / alias
    backup = root / 'recovery-checkpoints' / ('before-' + run + '-' + alias)
    backup.mkdir(parents=True)
    with closing(sqlite3.connect(root / 'ledger.sqlite3', isolation_level=None)) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        # Keep a full recoverable checkpoint before any DDL or row change.
        with closing(sqlite3.connect(backup / 'ledger.sqlite3')) as target:
            db.backup(target)
        db.execute('BEGIN IMMEDIATE')
        moved = False
        try:
            identity = db.execute('SELECT account,cap,origin FROM identity WHERE id=1').fetchone()
            from usd_ledger_v1 import nano
            if tuple(identity or ()) != (plan['config']['account_reference'], nano(plan['config']['pool_cap_usd']), 'real'):
                raise ValueError('REAL_LEDGER_IDENTITY_REQUIRED')
            stored = db.execute('SELECT contract FROM runs WHERE id=?', (run,)).fetchone()
            if not stored or stored[0] != digest(plan):
                raise ValueError('FROZEN_RUN_CONTRACT_DRIFT')
            if db.execute("SELECT 1 FROM trials WHERE state='active'").fetchone():
                raise ValueError('ACTIVE_TRIAL_RECOVERY_DENIED')
            outcome = db.execute('SELECT record,sha FROM development_outcomes WHERE run=? AND trial=?', (run,trial_id)).fetchone()
            if not outcome:
                raise ValueError('AUTHORITATIVE_OUTCOME_REQUIRED')
            row = json.loads(outcome['record'])
            if (digest(row) != outcome['sha'] or json.loads((folder / 'outcome.json').read_text(encoding='utf-8')) != row
                    or row.get('run_id') != run or row.get('trial_id') != trial_id or row.get('data_origin') != 'real-model'):
                raise ValueError('OUTCOME_LEDGER_DRIFT')
            requests = db.execute('SELECT id FROM requests WHERE run=? AND trial=?', (run,trial_id)).fetchall()
            tools = db.execute('SELECT call_id FROM tools WHERE run=? AND trial=?', (run,trial_id)).fetchall()
            eligible(requests, tools, row, folder)
            trial = db.execute('SELECT state,reserve_c,invoice_c,estimate_c FROM trials WHERE run=? AND id=?', (run,trial_id)).fetchone()
            if not trial or trial['state'] != 'finished' or any(trial[k] not in (None,0) for k in ['reserve_c','invoice_c','estimate_c']):
                raise ValueError('ZERO_EXPOSURE_FINISHED_TRIAL_REQUIRED')
            before_requests = [dict(r) for r in db.execute('SELECT * FROM requests ORDER BY id')]
            retained = {r['trial']:r['sha'] for r in db.execute('SELECT trial,sha FROM development_outcomes WHERE run=? AND trial!=?',(run,trial_id))}
            audit = {'schema':'vi-preloop-runtime-recovery/1','run_id':run,'trial_id':trial_id,'archived_trial_key':alias,
                     'provider_dispatches':0,'request_intents':0,'tool_intents':0,'api_charge_nano':0,
                     'raw_outcome_sha256':sha(folder/'outcome.json'),'raw_attestation_sha256':sha(folder/'runtime-attestation.json'),
                     'backup_sha256':sha(backup/'ledger.sqlite3'),'frozen_plan_sha256':sha(plan_path),
                     'frozen_source_sha256':plan['source_sha256'],'retained_outcome_sha256':retained,
                     'request_rows_before_sha256':digest(before_requests),'recovery_source_sha256':sha(Path(__file__)),
                     'archived_folder':str(destination),'recorded_at_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
            (backup/'audit-before.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            db.execute('CREATE TABLE IF NOT EXISTS preloop_runtime_recoveries(id TEXT PRIMARY KEY, record TEXT NOT NULL)')
            db.execute('PRAGMA defer_foreign_keys=ON')
            db.execute("UPDATE trials SET id=?,state='preloop_blocked' WHERE run=? AND id=?", (alias,run,trial_id))
            db.execute('UPDATE development_outcomes SET trial=? WHERE run=? AND trial=?',(alias,run,trial_id))
            db.execute('INSERT INTO preloop_runtime_recoveries VALUES (?,?)',(alias,json.dumps(audit,ensure_ascii=False)))
            if db.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('RECOVERY_FOREIGN_KEY_FAILURE')
            if [dict(r) for r in db.execute('SELECT * FROM requests ORDER BY id')] != before_requests:
                raise ValueError('REQUEST_ROWS_CHANGED')
            destination.parent.mkdir(exist_ok=True); folder.rename(destination); moved=True
            db.execute('COMMIT')
        except BaseException:
            db.execute('ROLLBACK')
            if moved: destination.rename(folder)
            raise
    result = {'audit':audit,'all_request_rows_unchanged':True,'retained_outcomes_unchanged':True,
              'raw_failure_preserved':True,'run_contract_unchanged':True,'trial_rearmed_before_any_dispatch':True}
    (backup/'completed.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


def prepare_unsubmitted_resume(repo, plan_path):
    plan=json.loads(Path(plan_path).read_text(encoding='utf-8')); root=Path(plan['config']['state_root'])/'runs'/plan['run_id']
    recovered=[]
    for trial in plan['planned_trials']:
        path=root/trial['trial_id']/'outcome.json'
        if path.is_file():
            row=json.loads(path.read_text(encoding='utf-8'))
            if not row.get('valid') and row.get('error_code')=='GATE_DENIED_ATTESTATION_EXPIRED_OR_INVALID':
                recovered.append(archive_preloop_failure(repo,plan_path,trial['trial_id']))
    return recovered
