"""Four targeted oracle trials, sequential, no cache pruning or model calls."""
import datetime
import json
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path
from plan_run import create
from execute_validation_plan import execute
from import_harbor_results import import_results
from preflight import inspect


def smoke(repo):
    runtime=Path('/tmp/vi-terminal-bench-runtime');run_id='stage3-targeted'
    dataset=runtime/'stage3-targeted-dataset'
    if dataset.exists():raise ValueError('Use a new smoke dataset/run ID; never overwrite')
    selected=['b005-vietnamese-collation','b006-vietnamese-csv-export']
    for task in selected:shutil.copytree(repo/'tasks'/task,dataset/task,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    health=[]
    for _ in range(3):
        result=inspect(runtime/'jobs',repo);health.append(result)
        if not result['ready']:raise ValueError('CLI health probe failed; do not run smoke')
    (repo/'reports/stage3-health-sequence.json').write_text(json.dumps(health,indent=2)+'\n',encoding='utf-8')
    plan=create(dataset,'vi','oracle','oracle-smoke',2,runtime/'jobs',run_id,selected,1)
    plan['job_deadline_sec']=300
    plan['conditions']={'1':'first-in-session-preexisting-image-cache-not-cold','2':'reuse-images-fresh-containers'}
    output=repo/'reports/stage3-smoke-run.json'
    if output.exists():raise ValueError('Smoke report already exists')
    output.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    execute(plan)
    rows,missing=import_results(plan)
    if missing or len(rows)!=4 or any(row['reward']!=1 or row['status']!='completed' for row in rows):raise ValueError('Smoke reward/coverage mismatch')
    (repo/'reports/stage3-smoke-trials.jsonl').write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows),encoding='utf-8')
    timings=[]
    for row in rows:
        raw=json.loads(Path(row['raw_reference']).read_text(encoding='utf-8'));phases={}
        for name in ['environment_setup','agent_setup','agent_execution','verifier']:
            item=raw.get(name) or {}
            if item.get('started_at') and item.get('finished_at'):
                parse=lambda value:datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
                phases[name]=(parse(item['finished_at'])-parse(item['started_at'])).total_seconds()
        timings.append({'task_id':row['task_id'],'repeat':row['repeat'],'duration_sec':row['duration_sec'],'phases':phases,'separate_verifier':raw['verifier_environment_mode']=='separate','reward':row['reward']})
    archive=repo/'jobs/stage3-targeted-smoke.tar.gz'
    if archive.exists():raise ValueError('Archive exists')
    with tarfile.open(archive,'w:gz') as handle:
        for name in sorted({attempt['job_name'] for trial in plan['planned_trials'] for attempt in trial['attempts']}):handle.add(runtime/'jobs'/name,arcname=name)
    report={'kind':'scoped-proxy-oracle-smoke-not-model-evaluation','all_passed':True,'timings':timings,'condition_note':plan['conditions'],'default_wsl_socket_repaired':False,'proxy_lifetime':'command-only','archive':str(archive)}
    (repo/'reports/stage3-smoke-summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('4/4 targeted smoke oracle trials passed; scoped endpoint only',flush=True)


if __name__=='__main__':smoke(Path(__file__).resolve().parents[1])
