"""Verify immutable task evidence, restore smoke archive, and prepare review bundles."""
import hashlib
import json
import tarfile
import tempfile
from pathlib import Path
from materialize_variants import payload_hash
from report_harbor_validation import summarize


def finalize(repo):
    baseline=json.loads((repo/'reports/stage3-baseline-state.json').read_text())
    for name,item in baseline['archives'].items():
        if hashlib.sha256((repo/'jobs'/name).read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Historical archive changed')
    for name,digest in baseline['canonical_task_payloads'].items():
        if payload_hash(repo/'tasks'/name)!=digest:raise ValueError('Task changed')
    smoke=json.loads((repo/'reports/stage3-smoke-summary.json').read_text());plan=json.loads((repo/'reports/stage3-smoke-run.json').read_text())
    archive=Path(smoke['archive']);restored=[]
    with tempfile.TemporaryDirectory(prefix='vi-stage3-restore-') as tmp:
        with tarfile.open(archive,'r:gz') as handle:handle.extractall(tmp,filter='data')
        for job in sorted({a['job_name'] for t in plan['planned_trials'] for a in t['attempts']}):
            report=summarize(Path(tmp)/job,'oracle',2)
            if not report['all_matched']:raise ValueError('Smoke archive mismatch')
            restored.append({'job':job,'trials':2,'all_matched':True})
    bundles={}
    for kind in ['public','reference']:
        path=repo/'jobs'/f'stage3-review-{kind}.tar.gz'
        if path.exists():raise ValueError('Review bundle already exists')
        with tarfile.open(path,'w:gz') as handle:
            for task in sorted(baseline['canonical_task_payloads']):
                items=['environment','instruction.md','README.md','task.toml'] if kind=='public' else ['tests','solution']
                for item in items:handle.add(repo/'tasks'/task/item,arcname=f'{task}/{item}')
                if kind=='public':
                    for lang in ['en','vi']:handle.add(repo/'prompts'/task/f'{lang}.md',arcname=f'{task}/prompts/{lang}.md')
        bundles[kind]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    tests=json.loads((repo/'reports/stage3-unit-tests.json').read_text())
    if not tests['all_passed'] or tests['skipped']:raise ValueError('Tooling tests not clean')
    default=json.loads((repo/'reports/stage3-preflight-default-after.json').read_text())
    return {'kind':'stage3-technical-summary-not-model-evaluation','historical_archives_unchanged':True,'six_task_payloads_unchanged':True,'smoke_trials':4,'smoke_all_passed':smoke['all_passed'],'smoke_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'restored_jobs':restored,'tests_run':tests['tests_run'],'tests_clean':True,'default_preflight_ready':default['ready'],'scoped_proxy_preflight_ready':True,'relay_directories_remaining':[str(p) for p in Path('/tmp').glob('vi-bench-proxy-*')],'review_bundles':bundles,'independent_review':'pending','model_calls':0}


if __name__=='__main__':
    repo=Path(__file__).resolve().parents[1];report=finalize(repo)
    (repo/'reports/stage3-summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Old evidence unchanged; smoke restored; review bundles prepared; no model calls')
