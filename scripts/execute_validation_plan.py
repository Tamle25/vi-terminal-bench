"""Execute only free oracle/nop local development plans, never model evaluations."""
import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path

from materialize_variants import payload_hash
from preflight import check
from runtime_process import run_bounded


def execute(plan):
    from harbor.models.task.task import Task
    repo=Path(__file__).resolve().parents[1]
    if plan['kind']!='development-validation-not-model-evaluation' or plan['configuration_spec']['agent'] not in {'oracle','nop'}:
        raise ValueError('Model plans are not executable by this development runner')
    if importlib.metadata.version('harbor')!=plan['harbor_version']:
        raise ValueError('Harbor version drift')
    jobs_root=Path(plan['jobs_root']);check(jobs_root,repo)
    dataset=Path(plan['dataset']);jobs={}
    for trial in plan['planned_trials']:
        task=dataset/trial['task_id']
        if payload_hash(task)!=trial['payload_sha256'] or hashlib.sha256((task/'instruction.md').read_bytes()).hexdigest()!=trial['instruction_sha256'] or Task(task).checksum!=trial['harbor_task_checksum']:
            raise ValueError('Task drift after planning: '+trial['task_id'])
        if len(trial['attempts'])!=1:
            raise ValueError('This runner executes initial attempts only; retries require explicit new job scheduling')
        job_name=trial['attempts'][0]['job_name'];jobs[job_name]=True
    for job_name in jobs:
        if (jobs_root/job_name).exists():raise ValueError('Refusing to overwrite existing job: '+job_name)
    for job_name in jobs:
        command=[str(Path(sys.executable).parent/'harbor'),'run','-p',str(dataset),'-a',plan['configuration_spec']['agent'],'-k','1','-n',str(plan['configuration_spec']['concurrency']),'-r','0','-o',str(jobs_root),'--job-name',job_name,'--quiet']
        print('Running '+job_name,flush=True)
        result=run_bounded(command,timeout=plan.get('job_deadline_sec',900),capture=False,log_path=jobs_root/(job_name+'.console.log'))
        if result['timed_out'] or result['returncode']!=0:raise RuntimeError('Owned job failed/deadline exceeded; inspect console log: '+job_name)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('plan',type=Path);args=p.parse_args()
    execute(json.loads(args.plan.read_text(encoding='utf-8')))
