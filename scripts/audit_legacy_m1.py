"""Explicit post-hoc bindings for legacy M1, never pretend these were prescheduled."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from import_harbor_results import import_results
from materialize_variants import payload_hash


def audit(repo):
    from harbor.models.task.task import Task
    summary=json.loads((repo/'reports/harbor-oracle-linux.json').read_text(encoding='utf-8'))
    snapshot=json.loads((repo/'reports/task-snapshot.json').read_text(encoding='utf-8'))['vi']
    metadata={row['task_id']:row for row in snapshot}
    counters=defaultdict(int);trials=[];bindings={}
    config={'agent':'oracle','model':None,'profile':'legacy-audit-not-model-evaluation'}
    config_hash=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    for raw in summary['trials']:
        task_id=raw['task_name'].split('/')[-1];row=metadata[task_id]
        if Task(repo/'tasks'/task_id).checksum!=raw['task_checksum']:
            raise ValueError('Current task differs from M1; cannot reuse source for canonical legacy payload hash')
        row={**row,'payload_sha256':payload_hash(repo/'tasks'/task_id)}
        counters[task_id]+=1
        trial_id='legacy-audit-'+raw['trial_name']
        trial=dict(trial_id=trial_id,task_id=task_id,family_id=row['family_id'],track='B',skill=row['primary_skill'],language='vi',configuration='m1-oracle-legacy-audit',configuration_sha256=config_hash,repeat=counters[task_id],payload_sha256=row['payload_sha256'],instruction_sha256=row['instruction_sha256'],harbor_task_checksum=raw['task_checksum'],attempts=[{'attempt':1,'job_name':'m1-oracle-linux','task_package':raw['task_name']}])
        trials.append(trial);bindings[trial_id+':1']=str(Path(summary['job'])/raw['trial_name']/'result.json')
    plan=dict(schema='vi-terminal-run/0.1',harbor_version='0.25.0',kind='legacy-audit-not-prescheduled',identity_origin='posthoc-explicit-bindings-repeat-is-audit-label-not-original-order',configuration_spec=config,jobs_root=str(Path(summary['job']).parent),planned_trials=trials)
    rows,missing=import_results(plan,bindings=bindings)
    if missing or len(rows)!=6 or any(row['reward']!=1 for row in rows):raise ValueError('M1 adapter audit failed')
    for name,value in [('m1-legacy-audit-plan.json',plan),('m1-legacy-bindings.json',bindings)]:
        (repo/'reports'/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (repo/'reports/m1-legacy-adapter-audit.json').write_text(json.dumps({'kind':plan['kind'],'rows':rows,'all_matched':True,'note':plan['identity_origin']},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Adapter verified against 6 real M1 raw trials with explicit post-hoc audit bindings')


if __name__=='__main__':audit(Path(__file__).resolve().parents[1])
