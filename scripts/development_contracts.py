"""Development-only task registry and frozen 36-trial contracts."""
import copy
import json
from pathlib import Path
import random
import re
import tomllib

from credential_artifacts import validate_native_inputs
from pilot_contracts import digest, snapshot
from provider_connectivity_v1 import MODEL, digest as file_digest
from terminal_agent_v1 import SYSTEM, TOOL, source_hashes as inherited_hashes
from usd_ledger_v1 import nano

TASKS=('b001-vn-invoice','b002-unicode-files','b003-windows1258','b004-accent-search',
       'b005-vietnamese-collation','b006-vietnamese-csv-export')
SCOPES={'development-smoke','development-batch'}
SOURCES=['development_contracts.py','development_ledger.py','development_agent.py','dev_benchmark.py',
         'development_sandbox.py',
         'development_verifier.py','capture_runtime_development.py','with_runtime_proxy_v2.py',
         'capture_runtime_attestation.py','development-benchmark.sh']


def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def validate_config(cfg):
    expected={'schema':'vi-development-benchmark/1','kind':'authorized-internal-development','development_only':True,
              'allow_pending_review':True,'model':MODEL,'reasoning':'none','compute_cost_status':'not_metered',
              'max_requests_per_trial':6,'max_output_tokens':2048,'max_input_tokens':272000,
              'max_payload_bytes':65536,'trial_timeout_sec':300,'command_timeout_sec':10,
              'command_output_bytes':16384,'max_command_bytes':8192,'artifact_max_bytes':16777216,
              'pids_limit':128,'concurrency':1,'automatic_retries':0,
              'settlement_policy':'observed-usage-conservative-input-v1'}
    if any(cfg.get(k)!=v for k,v in expected.items()): raise ValueError('UNSUPPORTED_DEVELOPMENT_CONFIG')
    if not cfg.get('authorization_reference') or not cfg.get('account_reference'): raise ValueError('AUTHORIZATION_REFERENCE_REQUIRED')
    if not 0<nano(cfg['pool_cap_usd'])<=nano('2') or nano(cfg['correction_margin_usd'])!=nano('.10'):
        raise ValueError('POOL_CAP_DENIED')
    if [cfg['pricing'][k] for k in ['input_nano_usd','cached_input_nano_usd','output_nano_usd']]!=[750,75,4500]:
        raise ValueError('PRICE_DRIFT')
    if type(cfg['seed']) is not int: raise ValueError('SEED')


def sources(repo):
    return {**inherited_hashes(repo),**{'scripts/'+name:file_digest(repo/'scripts'/name) for name in SOURCES},
            'configs/development-runtime-profiles.json':file_digest(repo/'configs/development-runtime-profiles.json')}


def registry(repo):
    rows=[json.loads(line) for line in (repo/'manifest.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    if {r['task_id'] for r in rows}!=set(TASKS) or len(rows)!=6: raise ValueError('TASK_REGISTRY_DRIFT')
    result={}
    for row in rows:
        tid=row['task_id']; spec=tomllib.loads((repo/'tasks'/tid/'task.toml').read_text(encoding='utf-8'))
        if row['track']!='B' or row['languages']!=['en','vi']: raise ValueError('TASK_SCOPE')
        if spec['artifacts'] not in [['/app/output','/app/data'],['/app/output','/app/incoming']]: raise ValueError('TASK_ARTIFACT_POLICY')
        if spec['environment']['cpus']!=1 or spec['environment']['memory_mb']!=1024: raise ValueError('TASK_RESOURCE_POLICY')
        result[tid]={'metadata':row,'toml':spec}
    return result


def backend_config(cfg,task):
    return {**cfg,'cpus':task['toml']['environment']['cpus'],'memory_mb':task['toml']['environment']['memory_mb']}


def planned(repo,cfg,scope,run_id):
    validate_config(cfg)
    if scope not in SCOPES or not re.fullmatch('[a-z0-9-]{1,100}',run_id): raise ValueError('DEVELOPMENT_SCOPE_OR_RUN')
    catalog=registry(repo); trials=[]; rng=random.Random(cfg['seed'])
    for repeat in range(1,2 if scope=='development-smoke' else 4):
        tasks=['b001-vn-invoice'] if scope=='development-smoke' else list(TASKS)
        rng.shuffle(tasks)
        for tid in tasks:
            langs=['en','vi']
            if rng.randrange(2): langs.reverse()
            for lang in langs:
                row=catalog[tid]['metadata']
                trials.append({'trial_id':f'{tid}--{lang}--r{repeat}--mini','task_id':tid,'family_id':row['family_id'],
                               'track':'B','skill':row['primary_skill'],'language':lang,'configuration':cfg['configuration'],
                               'repeat':repeat,'attempt':1,'review_status':row['review_status'],'author':row['author']})
    return {'schema':'vi-development-plan/1','run_id':run_id,'scope':scope,'origin':'real-model',
            'development_only':True,'independently_reviewed':False,'config':copy.deepcopy(cfg),
            'snapshot':snapshot(repo),'manifest_sha256':file_digest(repo/'manifest.jsonl'),'source_sha256':sources(repo),'prompt_tools_hash':digest([SYSTEM,TOOL]),
            'planned_trials':trials}


def request_reserve(cfg): return cfg['max_input_tokens']*750+cfg['max_output_tokens']*4500


def conservative_cost(receipt,cfg):
    """All input at uncached price: provisional upper token estimate, not invoice."""
    body=receipt.get('response',{})
    if receipt.get('http_status')!=200 or not receipt.get('provider_request_id') or body.get('model')!=MODEL or body.get('service_tier')!='default' or body.get('status') not in {'completed','incomplete'}:
        return None
    usage=body.get('usage')
    if not isinstance(usage,dict): return None
    i,o,t=usage.get('input_tokens'),usage.get('output_tokens'),usage.get('total_tokens')
    detail=usage.get('input_tokens_details'); out=usage.get('output_tokens_details')
    if not isinstance(detail,dict) or not isinstance(out,dict): return None
    c=detail.get('cached_tokens'); w=detail.get('cache_write_tokens',0); r=out.get('reasoning_tokens')
    if any(type(n) is not int or n<0 for n in [i,o,t,c,w,r]): return None
    if t!=i+o or c>i or r>o or w!=0 or i>cfg['max_input_tokens'] or o>cfg['max_output_tokens']: return None
    return i*750+o*4500


def public_inputs(repo):
    return {name:file_digest(repo/name) for name in validate_native_inputs(repo)}
