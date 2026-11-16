"""Create immutable trial identities BEFORE running Harbor (one job per repeat)."""
import argparse
import datetime
import hashlib
import importlib.metadata
import json
import re
from pathlib import Path

from materialize_variants import payload_hash

REPO=Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def create(dataset,language,agent,configuration,repeats,jobs_root,run_id,selected=None,concurrency=2):
    from harbor.models.task.task import Task
    if importlib.metadata.version('harbor')!='0.25.0':
        raise ValueError('Run planning requires locked Harbor 0.25.0')
    if agent not in {'oracle','nop'} or not 1<=repeats<=3:
        raise ValueError('This execution profile supports only oracle/nop development validation')
    if not all(re.fullmatch('[a-z0-9-]+',value) for value in [configuration,run_id]):
        raise ValueError('Run/configuration IDs must be lowercase ASCII slugs')
    roster=[json.loads(line) for line in (REPO/'manifest.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    if selected:
        if set(selected)-{row['task_id'] for row in roster}:raise ValueError('Unknown selected task')
        roster=[row for row in roster if row['task_id'] in selected]
    if type(concurrency) is not int or concurrency<1:raise ValueError('Invalid concurrency')
    snapshots={}
    for row in roster:
        task_id=row['task_id'];folder=dataset/task_id
        instruction=(folder/'instruction.md').read_bytes()
        if language not in row['languages'] or instruction!=(REPO/'prompts'/task_id/f'{language}.md').read_bytes():
            raise ValueError('Instruction/declared language mismatch: '+task_id)
        snapshots[task_id]={
            'payload_sha256':payload_hash(folder),
            'instruction_sha256':hashlib.sha256(instruction).hexdigest(),
            'harbor_task_checksum':Task(folder).checksum,
            'task_package':Task(folder).config.task.name,
            'task_version':row['task_version'],
        }
    spec={'agent':agent,'model':None,'harbor':'0.25.0','retries':0,'concurrency':concurrency,'network':'compose-none','profile':'development-validation'}
    trials=[]
    for repeat in range(1,repeats+1):
        job_name=f'{run_id}-{configuration}-{language}-r{repeat}'
        for row in roster:
            task_id=row['task_id']
            trials.append(dict(trial_id=f'{run_id}-{configuration}-{language}-{task_id}-r{repeat}',task_id=task_id,family_id=row['family_id'],track=row['track'],skill=row['primary_skill'],language=language,configuration=configuration,configuration_sha256=digest(spec),repeat=repeat,attempts=[{'attempt':1,'job_name':job_name,'task_package':snapshots[task_id]['task_package']}],**snapshots[task_id]))
    return {'schema':'vi-terminal-run/0.1','kind':'development-validation-not-model-evaluation','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'run_id':run_id,'dataset':str(dataset.resolve()),'jobs_root':str(jobs_root.resolve()),'harbor_version':'0.25.0','configuration_spec':spec,'expected_repeats':repeats,'task_manifest':roster,'planned_trials':trials}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--language',choices=['en','vi'],required=True)
    p.add_argument('--agent',choices=['oracle','nop'],required=True);p.add_argument('--configuration',required=True);p.add_argument('--repeats',type=int,default=3)
    p.add_argument('--jobs-root',type=Path,required=True);p.add_argument('--run-id',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Refusing to overwrite run manifest')
    plan=create(a.dataset,a.language,a.agent,a.configuration,a.repeats,a.jobs_root,a.run_id)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"Planned {len(plan['planned_trials'])} trials before execution")
