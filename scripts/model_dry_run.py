"""Offline profile validation and schedule preview. Never load secrets or call a model."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from urllib.parse import urlparse
from materialize_variants import payload_hash

FIELDS={'id','agent','agent_version','model','provider','endpoint','reasoning_effort','system_prompt_path','agent_kwargs','max_tokens','max_turns','timeout_sec','architecture','credential_env_name'}
PROFILE_FIELDS={'schema','scope','run_id','languages','repeats','concurrency','budget','configurations'}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def check_effective(expected,observed):
    # Pure-data contract; real agent-specific Harbor mapping must be verified when selected.
    if set(expected)!=FIELDS or set(observed)!=FIELDS:raise ValueError('Incomplete effective profile contract')
    if fingerprint(expected)!=fingerprint(observed):raise ValueError('Effective model profile drift')


def dry_run(profile,repo):
    if set(profile)!=PROFILE_FIELDS or profile['schema']!='vi-terminal-model-profile/0.1':raise ValueError('Unsupported or unknown profile fields; secret values are forbidden')
    if profile['scope']!='native-six' or profile['languages']!=['en','vi'] or profile['repeats']!=3:raise ValueError('This preview supports native-six EN/VI, three repeats')
    if not re.fullmatch('[a-z0-9-]+',profile['run_id']):raise ValueError('Invalid run ID')
    if type(profile['concurrency']) is not int or profile['concurrency']<1:raise ValueError('Invalid concurrency')
    if set(profile['budget'])!={'max_inference_usd','max_compute_usd','smoke_max_usd'}:raise ValueError('Budget fields mismatch')
    missing=[]
    for key,value in profile['budget'].items():
        if value is None:missing.append('budget.'+key)
        elif type(value) not in (int,float) or not math.isfinite(value) or value<=0:raise ValueError('Invalid budget')
    configs=profile['configurations']
    if len(configs)!=2 or len({c['id'] for c in configs})!=2:raise ValueError('Two distinct configuration IDs required')
    for config in configs:
        if set(config)!=FIELDS:raise ValueError('Unknown configuration fields; never put API key values in profile')
        if not re.fullmatch('[a-z0-9-]+',config['id']):raise ValueError('Invalid configuration ID')
        for field in FIELDS-{'agent_kwargs','max_tokens','max_turns','timeout_sec'}:
            if config[field] is not None and (type(config[field]) is not str or not config[field].strip()):raise ValueError('Profile string field must be nonempty or null')
        for field,value in config.items():
            if field not in {'id','agent_kwargs'} and value is None:missing.append(config['id']+'.'+field)
        for field in ['max_tokens','max_turns','timeout_sec']:
            value=config[field]
            if value is not None and (type(value) is not int or value<=0):raise ValueError('Invalid model budget field')
        if config['endpoint']:
            parsed=urlparse(config['endpoint'])
            if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:raise ValueError('Endpoint must not embed credentials/query secrets')
        if config['credential_env_name'] and not re.fullmatch('[A-Z][A-Z0-9_]*',config['credential_env_name']):raise ValueError('Use an environment variable NAME, never a secret value')
        if config['architecture'] not in {None,'host-agent-offline-sandbox','preinstalled-agent-controlled-egress'}:raise ValueError('Unsupported architecture')
        if config['system_prompt_path']:
            path=(repo/config['system_prompt_path']).resolve()
            if not path.is_relative_to(repo.resolve()) or not path.is_file() or path.suffix!='.md':raise ValueError('System prompt must be a workspace Markdown file')
        # Kwargs can carry provider-specific secrets; defer nonempty kwargs until a concrete safe mapping exists.
        if config['agent_kwargs']!={}:raise ValueError('Agent-specific kwargs require an explicit reviewed adapter')
    roster=[json.loads(line) for line in (repo/'manifest.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    if len(roster)!=6 or any(row['track']!='B' for row in roster):raise ValueError('Expected native-six roster')
    trials=[]
    for config in configs:
        prompt_hash=None
        if config['system_prompt_path']:prompt_hash=hashlib.sha256((repo/config['system_prompt_path']).read_bytes()).hexdigest()
        config_hash=fingerprint({'model_profile':config,'system_prompt_sha256':prompt_hash,'concurrency':profile['concurrency']})
        for language in profile['languages']:
            for repeat in range(1,4):
                for task in roster:
                    task_id=task['task_id'];prompt=(repo/'prompts'/task_id/f'{language}.md').read_bytes()
                    trials.append({'trial_id':f"{profile['run_id']}-{config['id']}-{language}-{task_id}-r{repeat}",'task_id':task_id,'family_id':task['family_id'],'track':'B','skill':task['primary_skill'],'language':language,'configuration':config['id'],'repeat':repeat,'payload_sha256':payload_hash(repo/'tasks'/task_id),'instruction_sha256':hashlib.sha256(prompt).hexdigest(),'configuration_sha256':config_hash,'system_prompt_sha256':prompt_hash,'attempts':[{'attempt':1,'job_name':f"{profile['run_id']}-{config['id']}-{language}-r{repeat}"}]})
    pending=[row['task_id'] for row in roster if row['review_status']!='accepted' or not row['reviewer']]
    return {'schema':'vi-terminal-model-dry-run/0.1','kind':'offline-dry-run-not-executable','ready_for_model_calls':False,'profile_complete':not missing,'missing_inputs':missing,'pending_review':pending,'runtime_attestation':'required-at-execution-not-inferred-from-history','agent_specific_adapter':'not-verified-with-a-real-profile','expected_configurations':[c['id'] for c in configs],'planned_trials':trials,'trial_count':len(trials),'max_infrastructure_retries':2,'smoke_trials':'1-2-separate-from-72','proposed_steps':['validate concrete agent/profile mapping','preflight exact runtime/network profile','review task snapshots','run budgeted smoke only when authorized','schedule frozen 72-trial native pilot'],'secrets_read':False,'model_calls':0}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--profile',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report=dry_run(json.loads(a.profile.read_text(encoding='utf-8')),Path(__file__).resolve().parents[1])
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"Offline preview: {report['trial_count']} planned trials; missing inputs={len(report['missing_inputs'])}; model calls=0; not executable")
