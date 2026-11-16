"""Read-only bounded diagnostics. No credential/config/environment dumps."""
import argparse
import datetime
import http.client
import json
import os
import platform
import shutil
import socket
import time
from pathlib import Path
from runtime_process import run_bounded


class UnixConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout);self.sock.connect('/var/run/docker.sock')


def diagnose(timeout=5):
    executable=shutil.which('docker')
    result={'recorded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'platform':platform.platform(),'docker_cli':executable,'environment_override_names':[name for name in ['DOCKER_HOST','DOCKER_CONTEXT','DOCKER_API_VERSION'] if os.environ.get(name)],'probes':{}}
    if executable:
        path=Path(executable)
        result['resolved_cli']=str(path.resolve())
        try:
            with path.open('rb') as stream:result['executable_magic_hex']=stream.read(4).hex()
        except OSError as exc:result['executable_read_error']=type(exc).__name__
        for name,command in [('cli_version',['docker','version','--format','{{json .Server}}']),('cli_context',['docker','context','show'])]:
            result['probes'][name]=run_bounded(command,timeout=timeout)
    result['unix_socket_present']=Path('/var/run/docker.sock').exists()
    if os.name=='posix' and result['unix_socket_present']:
        started=time.monotonic();connection=UnixConnection('localhost',timeout=timeout)
        try:
            connection.request('GET','/version',headers={'Connection':'close'})
            response=connection.getresponse();data=json.loads(response.read(65536))
            result['probes']['unix_api']={'status':response.status,'version':data.get('Version'),'os':data.get('Os'),'elapsed_sec':time.monotonic()-started}
        except (OSError,ValueError,http.client.HTTPException) as exc:
            result['probes']['unix_api']={'error_type':type(exc).__name__,'elapsed_sec':time.monotonic()-started}
        finally:connection.close()
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--timeout',type=float,default=5);args=p.parse_args()
    if args.output.exists():raise ValueError('Use a fresh diagnosis report path')
    report=diagnose(args.timeout);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
