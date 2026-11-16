"""Stable identities and runtime/review evidence contracts. No network operations."""
import datetime as dt
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from materialize_variants import payload_hash

STATUSES={'pass','fail','missing_input','unverified','not_applicable'}
RUNTIME_FIELDS={'id','version','mode','distro','user','endpoint_class','verifier_network','control_socket_in_sandbox','cli_timeout_sec','validated_concurrency'}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()


def snapshot(repo):
    roster=[json.loads(line) for line in (repo/'manifest.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    tasks={}
    for row in roster:
        name=row['task_id']
        tasks[name]={'version':row['task_version'],'author':row['author'],'family_id':row['family_id'],'skill':row['primary_skill'],'payload_sha256':payload_hash(repo/'tasks'/name),'prompts':{lang:hashlib.sha256((repo/'prompts'/name/f'{lang}.md').read_bytes()).hexdigest() for lang in row['languages']}}
    return {'id':digest(tasks),'tasks':tasks}


def runtime_fingerprint(profile):
    if set(profile)!=RUNTIME_FIELDS:raise ValueError('Runtime profile fields mismatch; ephemeral endpoint belongs in observation')
    if profile['mode'] not in {'native-wsl','scoped-relay'} or profile['verifier_network']!='none' or profile['control_socket_in_sandbox'] is not False:raise ValueError('Unsupported runtime/network policy')
    for field in ['version','cli_timeout_sec','validated_concurrency']:
        if type(profile[field]) is not int or profile[field]<1:raise ValueError('Invalid runtime numeric field')
    if any(type(profile[key]) is not str or not profile[key] for key in ['id','mode','distro','user','endpoint_class']):raise ValueError('Runtime identity missing')
    return digest(profile)


def validate_attestation(profile,evidence,run_id,snapshot_id,now=None,concurrency=1):
    fingerprint=runtime_fingerprint(profile)
    if evidence is None:return 'missing_input','Fresh runtime attestation required'
    if evidence.get('kind')!='runtime-capture':return 'unverified','Simulation/historical evidence cannot attest a model run'
    expected={'run_id':run_id,'snapshot_id':snapshot_id,'runtime_profile_id':profile['id'],'runtime_profile_sha256':fingerprint}
    if any(evidence.get(key)!=value for key,value in expected.items()):return 'fail','Attestation identity/profile/snapshot mismatch'
    try:
        issued=dt.datetime.fromisoformat(evidence['issued_at_utc'].replace('Z','+00:00'))
        expires=dt.datetime.fromisoformat(evidence['expires_at_utc'].replace('Z','+00:00'))
        current=now or dt.datetime.now(dt.timezone.utc)
        if issued.tzinfo is None or expires.tzinfo is None or not issued<=current<expires or not 0<(expires-issued).total_seconds()<=900:return 'fail','Attestation expired/future/invalid validity window'
    except (KeyError,ValueError,TypeError):return 'fail','Invalid attestation timestamps'
    observed=evidence.get('observation',{})
    if evidence.get('preflight',{}).get('ready') is not True:return 'fail','Current preflight failed'
    if observed.get('user')!=profile['user'] or observed.get('endpoint_class')!=profile['endpoint_class'] or observed.get('docker_os')!='linux' or observed.get('filesystem_capabilities_ok') is not True or observed.get('verifier_network')!='none' or observed.get('control_socket_in_sandbox') is not False:return 'fail','Runtime observation mismatch'
    if profile['mode']=='scoped-relay' and (observed.get('socket_mode')!='0600' or observed.get('lifecycle')!='command-only' or not observed.get('endpoint')):return 'fail','Relay lifecycle/socket evidence missing'
    if type(observed.get('endpoint')) is not str:return 'fail','Observed endpoint missing'
    endpoint=urlparse(observed['endpoint'])
    if endpoint.scheme!='unix' or endpoint.netloc or endpoint.query or endpoint.fragment:return 'fail','Only the selected local Unix endpoint is supported'
    if profile['mode']=='native-wsl' and endpoint.path not in {'/var/run/docker.sock','/run/docker.sock'}:return 'fail','Native endpoint differs from profile'
    if profile['mode']=='scoped-relay' and (Path(endpoint.path).name!='docker.sock' or Path(endpoint.path).parent.parent!=Path('/tmp') or not Path(endpoint.path).parent.name.startswith('vi-bench-proxy-')):return 'fail','Relay endpoint differs from managed profile'
    if concurrency>profile['validated_concurrency']:return 'unverified','Selected concurrency exceeds validated runtime profile'
    return 'pass','Runtime evidence matches this run; not an authorization token'


def configuration_contract(config,prompt_sha256,runtime,concurrency,tool_access,resources):
    # Actual endpoint instance/timestamps intentionally not accepted here.
    return {'schema':'pilot-effective-contract/0.1','model_profile':config,'system_prompt_sha256':prompt_sha256,'runtime_profile_sha256':runtime_fingerprint(runtime),'concurrency':concurrency,'tool_access':tool_access,'resources':resources}


def compare_effective(expected,observed):
    if digest(expected)!=digest(observed):raise ValueError('Effective configuration contract drift')
