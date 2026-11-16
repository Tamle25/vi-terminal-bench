"""Separate offline verifier: bounded artifact tar on stdin, no distro bind mount."""
import io
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tarfile
import uuid

from terminal_sandbox_v1 import bounded
from terminal_verifier_v1 import result_from_process

RUNNER=r'''
import io,json,sys,tarfile,subprocess
from pathlib import Path,PurePosixPath
try:
 raw=sys.stdin.buffer.read(20971521)
 if len(raw)>20971520: raise ValueError('artifact size')
 total=0; seen=set(); files=[]
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as archive:
  for member in archive:
   name=PurePosixPath(member.name)
   if name.is_absolute() or '..' in name.parts or '\\' in member.name or not (member.isfile() or member.isdir()) or str(name) in seen: raise ValueError('artifact policy')
   seen.add(str(name))
   if len(seen)>4096: raise ValueError('file count')
   if member.isfile():
    total+=member.size
    if total>16777216: raise ValueError('artifact size')
    files.append((name,archive.extractfile(member).read(member.size)))
 for name,data in files:
  path=Path('/app').joinpath(*name.parts); path.parent.mkdir(parents=True,exist_ok=True)
  with path.open('xb') as output: output.write(data)
except Exception:
 print(json.dumps({'verifier_error':'artifact_transfer_policy'})); raise SystemExit(2)
raise SystemExit(subprocess.call([sys.executable,'-I','/tests/grader.py']))
'''


def pack(artifact,max_bytes=16777216):
    artifact=Path(artifact)
    if any(p.is_symlink() for p in [artifact,*artifact.parents]): raise ValueError('ARTIFACT_SYMLINK')
    paths=list(artifact.rglob('*'))
    if len(paths)>4096 or any(p.is_symlink() or not (p.is_file() or p.is_dir()) for p in paths): raise ValueError('ARTIFACT_POLICY')
    if sum(p.stat().st_size for p in paths if p.is_file())>max_bytes: raise ValueError('ARTIFACT_SIZE')
    raw=io.BytesIO()
    with tarfile.open(fileobj=raw,mode='w') as archive:
        for path in sorted(paths): archive.add(path,arcname=path.relative_to(artifact).as_posix(),recursive=False)
    if len(raw.getvalue())>20971520: raise ValueError('ARTIFACT_STREAM_SIZE')
    return raw.getvalue()


def verify(artifact,jobs_root,image_id,run):
    artifact,jobs_root=Path(artifact),Path(jobs_root)
    if not artifact.is_dir() or not artifact.resolve().is_relative_to(jobs_root.resolve()) or artifact.resolve()==jobs_root.resolve(): raise ValueError('ARTIFACT_ROOT')
    if not re.fullmatch('sha256:[0-9a-f]{64}',image_id): raise ValueError('VERIFIER_IMAGE_ID')
    raw=pack(artifact); name='vi-stage11-verifier-'+uuid.uuid4().hex
    command=['docker','run','--rm','--name',name,'--label','vi-bench.run='+run,'--network','none','--read-only',
             '--tmpfs','/app:rw,nosuid,nodev,size=16m','--memory','128m','--cpus','1','--pids-limit','128',
             '--cap-drop','ALL','--security-opt','no-new-privileges','-i','--entrypoint','python',image_id,'-I','-c',RUNNER]
    env={k:os.environ[k] for k in ['PATH','HOME','USER','DOCKER_HOST','DOCKER_CONTEXT'] if k in os.environ}
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,start_new_session=os.name=='posix')
    timed_out=False
    try: out,err=process.communicate(input=raw,timeout=60)
    except subprocess.TimeoutExpired:
        timed_out=True
        if os.name=='posix':
            try: os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError: pass
        else: process.kill()
        out,err=process.communicate()
    if timed_out or process.returncode not in (0,1):
        check=bounded(['docker','inspect',name],5)
        if check['exit_code']==0 and not check['timed_out']:
            rows=json.loads(check['stdout_bytes'])
            if len(rows)!=1 or rows[0]['Config'].get('Labels',{}).get('vi-bench.run')!=run: raise ValueError('VERIFIER_CLEANUP_IDENTITY')
            cleaned=bounded(['docker','rm','-f',rows[0]['Id']],5)
            if cleaned['exit_code'] or cleaned['timed_out']: raise ValueError('VERIFIER_CLEANUP_FAILED')
    result={'exit_code':process.returncode,'timed_out':timed_out,'stdout_bytes':out[:65536],'stderr_bytes':err[:65536],
            'truncated':[len(out)>65536,len(err)>65536]}
    return result_from_process(result)
