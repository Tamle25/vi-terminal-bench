"""Collect mounted tmpfs output through a trusted in-container tar producer.

docker cp of /app can omit nested tmpfs content. All model subprocesses are
terminated before collection; only namespace init and the trusted collector live.
"""
from terminal_sandbox_v1 import DockerSandbox, bounded, extract_data

COLLECTOR=r'''
import os,signal,sys,tarfile,stat
from pathlib import Path
for name in os.listdir('/proc'):
 if name.isdigit() and int(name) not in {1,os.getpid()}:
  try: os.kill(int(name),signal.SIGKILL)
  except ProcessLookupError: pass
paths=list(Path('/app').rglob('*'))
if len(paths)>4096: raise SystemExit(4)
total=sum(p.lstat().st_size for p in paths if stat.S_ISREG(p.lstat().st_mode))
if total>16777216: raise SystemExit(4)
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as archive:
 archive.add('/app',arcname='.',recursive=True)
'''


class DevelopmentSandbox(DockerSandbox):
    def collect(self,target):
        self.inspect()
        result=bounded([self.cli,'exec',self.cid,'python','-I','-c',COLLECTOR],10,
                       self.config['artifact_max_bytes']+4194304)
        if result['exit_code']!=0 or result['timed_out'] or result['truncated'][0]:
            raise ValueError('ARTIFACT_STREAM_FAILED')
        paused=bounded([self.cli,'pause',self.cid],5)
        if paused['exit_code'] or paused['timed_out']: raise ValueError('SANDBOX_PAUSE_FAILED')
        self.poisoned=True
        extract_data(result['stdout_bytes'],target,self.config['artifact_max_bytes'])
