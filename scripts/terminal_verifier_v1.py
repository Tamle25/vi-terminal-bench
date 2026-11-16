"""Trusted B001 verifier in a separate network-free container, data-only input."""
import json
from pathlib import Path
import re
import uuid

from terminal_sandbox_v1 import bounded


def result_from_process(result):
    if result['timed_out'] or result['exit_code'] not in (0,1) or any(result['truncated']):
        return {'status':'verifier_infra_failure','reward':None}
    try:
        body = json.loads(result['stdout_bytes'])
    except (ValueError,UnicodeError):
        return {'status':'verifier_infra_failure','reward':None}
    if not isinstance(body,dict) or type(body.get('passed')) is not bool or body['passed'] != (result['exit_code']==0):
        return {'status':'verifier_infra_failure','reward':None}
    return {'status':'verified','reward':1 if result['exit_code']==0 else 0,'checks':body}


def verify(artifact, jobs_root, image_id, run):
    if not re.fullmatch('sha256:[0-9a-f]{64}', image_id): raise ValueError('VERIFIER_IMAGE_ID_REQUIRED')
    artifact, jobs_root = Path(artifact), Path(jobs_root)
    if not artifact.is_dir() or artifact.resolve()==jobs_root.resolve() or not artifact.resolve().is_relative_to(jobs_root.resolve()) or ',' in str(artifact): raise ValueError('VERIFIER_ARTIFACT_ROOT')
    if str(artifact.resolve()).startswith('/mnt/') or not artifact.is_absolute(): raise ValueError('NATIVE_LINUX_ARTIFACT_REQUIRED')
    if any(p.is_symlink() for p in [artifact,*artifact.parents]) or any(p.is_symlink() for p in artifact.rglob('*')):
        raise ValueError('VERIFIER_SYMLINK')
    name='vi-stage10-verifier-'+uuid.uuid4().hex
    command = ['docker','run','--rm','--name',name,'--label','vi-bench.run='+run,'--network','none','--read-only',
               '--memory','128m','--cpus','1','--pids-limit','128','--cap-drop','ALL',
               '--security-opt','no-new-privileges','--mount','type=bind,src='+str(artifact)+',dst=/app,readonly',
               '--entrypoint','python',image_id,'-I','/tests/grader.py']
    process=bounded(command,60)
    if process['timed_out'] or process['exit_code'] not in (0,1):
        # Killing the CLI alone does not stop its container. Remove only an
        # inspected container bearing this run label and the generated name.
        check=bounded(['docker','inspect',name],5)
        if check['exit_code']==0 and not check['timed_out']:
            rows=json.loads(check['stdout_bytes'])
            if len(rows)!=1 or rows[0]['Config'].get('Labels',{}).get('vi-bench.run')!=run or not re.fullmatch('[0-9a-f]{64}',rows[0]['Id']):
                raise ValueError('VERIFIER_CLEANUP_OWNERSHIP')
            cleaned=bounded(['docker','rm','-f',rows[0]['Id']],5)
            if cleaned['exit_code']!=0 or cleaned['timed_out']: raise ValueError('VERIFIER_CLEANUP_FAILED')
    return result_from_process(process)


def normalized(loop, verifier, *, snapshot_id, artifact_sha256):
    # Valid reward zero is independent of whether a model said it had finished.
    return {'schema':'vi-terminal-trial/1','origin':loop['origin'],'scope':'model-smoke',
            'trial_id':loop['trial_id'],'language':loop['language'],'snapshot_id':snapshot_id,
            'stop_reason':loop['stop_reason'],'tool_calls':loop['tool_calls'],
            'trajectory':loop['trajectory'],'artifact_sha256':artifact_sha256,
            'reward':verifier.get('reward'),'verifier_status':verifier['status'],
            'failure_class':loop.get('failure_class'),'terminal_path_observed':loop['tool_calls']>0,
            'benchmark_result':loop['origin']=='real' and verifier['status']=='verified' and loop.get('failure_class') in {None,'agent'},
            'billing_state':'provisional-estimates-until-reconciliation'}
