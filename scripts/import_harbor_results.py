"""Pinned Harbor 0.25.0 adapter; identities come from a pre-execution run manifest."""
import argparse
import datetime
import json
import math
from pathlib import Path

KNOWN_ERRORS={
    'AgentTimeoutError':'agent_timeout','AgentExecutionTimeoutError':'agent_timeout',
    'EnvironmentBuildError':'infra_error','EnvironmentStartError':'infra_error',
    'VerifierTimeoutError':'verifier_error','RewardFileNotFoundError':'verifier_error',
    'RewardFileEmptyError':'verifier_error','RewardFileInvalidError':'verifier_error',
}


def normalized_reward(value):
    if type(value) not in (int,float) or not math.isfinite(value) or value not in (0,1):
        raise ValueError('Completed reward must be finite numeric 0/1, not bool/null')
    return int(value)


def normalize(data,planned,attempt,reference,classifications=None):
    if data.get('task_name')!=attempt['task_package'] or data.get('task_checksum')!=planned['harbor_task_checksum']:
        raise ValueError('Task identity/checksum mismatch: '+reference)
    if not data.get('finished_at'):
        raise ValueError('Unfinished raw trial: '+reference)
    raw_agent=(data.get('config') or {}).get('agent') or {}
    # Fingerprint of effective agent/config is supplied by the planner, not inferred from filenames.
    exception=data.get('exception_info')
    if exception:
        error_type=exception.get('exception_type')
        rules={**KNOWN_ERRORS,**(classifications or {})}
        if error_type not in rules:
            raise ValueError(f'Unclassified Harbor error {error_type!r}; record an explicit classification')
        status=rules[error_type]
        if status not in {'agent_timeout','agent_error','infra_error','verifier_error'}:
            raise ValueError('Invalid error classification')
        reward=None if status in {'infra_error','verifier_error'} else 0
    else:
        status='completed'
        rewards=(data.get('verifier_result') or {}).get('rewards') or {}
        if set(rewards)!={'reward'}:
            raise ValueError('Expected one scalar reward')
        reward=normalized_reward(rewards['reward'])
    duration=(datetime.datetime.fromisoformat(data['finished_at'].replace('Z','+00:00'))-datetime.datetime.fromisoformat(data['started_at'].replace('Z','+00:00'))).total_seconds()
    keys=['trial_id','task_id','family_id','track','skill','language','configuration','configuration_sha256','repeat','payload_sha256','instruction_sha256','harbor_task_checksum']
    row={key:planned[key] for key in keys}
    row.update(attempt=attempt['attempt'],status=status,reward=reward,duration_sec=duration,cost_usd=(data.get('agent_result') or {}).get('cost_usd'),raw_reference=reference,raw_trial_name=data['trial_name'],raw_exception_type=exception.get('exception_type') if exception else None)
    return row


def import_results(plan,classifications=None,bindings=None):
    if plan.get('schema')!='vi-terminal-run/0.1' or plan.get('harbor_version')!='0.25.0':
        raise ValueError('Unsupported plan/Harbor schema')
    rows=[];consumed=set();missing=[];root=Path(plan['jobs_root'])
    allowed_bindings={f"{trial['trial_id']}:{attempt['attempt']}" for trial in plan['planned_trials'] for attempt in trial['attempts']}
    if bindings is not None and set(bindings)-allowed_bindings:
        raise ValueError('Bindings contain unplanned attempts')
    for trial in plan['planned_trials']:
        for attempt in trial['attempts']:
            key=f"{trial['trial_id']}:{attempt['attempt']}"
            if bindings is not None:
                paths=[Path(bindings[key])] if key in bindings else []
            else:
                paths=[]
                for path in (root/attempt['job_name']).glob('*/result.json'):
                    item=json.loads(path.read_text(encoding='utf-8'))
                    if item.get('task_name')==attempt['task_package']:paths.append(path)
            if not paths:
                missing.append(key);continue
            if len(paths)!=1 or str(paths[0].resolve()) in consumed:
                raise ValueError('Ambiguous/duplicate raw binding: '+key)
            path=paths[0];data=json.loads(path.read_text(encoding='utf-8'))
            config_agent=plan['configuration_spec']['agent']
            if (data.get('config',{}).get('agent') or {}).get('name')!=config_agent:
                raise ValueError('Effective agent differs from plan')
            if plan['configuration_spec'].get('model')!=(data.get('config',{}).get('agent') or {}).get('model_name'):
                raise ValueError('Effective model differs from plan')
            effective=data.get('config') or {}
            agent=effective.get('agent') or {}
            environment=effective.get('environment') or {}
            verifier=effective.get('verifier') or {}
            if agent.get('kwargs',{})!=plan['configuration_spec'].get('agent_kwargs',{}) or agent.get('skills',[]) or agent.get('load_trajectory') or agent.get('resume_trajectory'):
                raise ValueError('Effective agent options/history differ from planned profile')
            if effective.get('extra_instructions') or effective.get('extra_instruction_paths') or effective.get('timeout_multiplier',1)!=1:
                raise ValueError('Effective instructions/timeouts differ from planned snapshot')
            if environment.get('type','docker')!='docker' or any(environment.get(key) is not None for key in ['override_cpus','override_memory_mb','override_gpus','override_storage_mb']):
                raise ValueError('Effective sandbox/resources differ from planned profile')
            if verifier.get('disable') or verifier.get('override_timeout_sec') is not None or agent.get('override_timeout_sec') is not None:
                raise ValueError('Effective verification/budget override differs from plan')
            rows.append(normalize(data,trial,attempt,str(path),classifications));consumed.add(str(path.resolve()))
    if bindings is None:
        jobs={attempt['job_name'] for trial in plan['planned_trials'] for attempt in trial['attempts']}
        observed={str(path.resolve()) for job in jobs for path in (root/job).glob('*/result.json')}
        if observed!=consumed:raise ValueError('Unplanned raw trials would be discarded')
    return rows,missing


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--classifications',type=Path);p.add_argument('--bindings',type=Path)
    args=p.parse_args();plan=json.loads(args.plan.read_text(encoding='utf-8'))
    rules=json.loads(args.classifications.read_text()) if args.classifications else None
    bindings=json.loads(args.bindings.read_text()) if args.bindings else None
    rows,missing=import_results(plan,rules,bindings)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(''.join(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n' for row in rows),encoding='utf-8')
    args.output.with_suffix('.coverage.json').write_text(json.dumps({'missing_attempts':missing,'observed_attempts':len(rows)},indent=2)+'\n',encoding='utf-8')
    print(f'Imported {len(rows)} attempts; missing={len(missing)} (repeat IDs were not inferred)')
