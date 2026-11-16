"""Explicit profile capture inside an already selected runtime; no root/fallback launcher."""
import argparse
import datetime as dt
import json
import os
import stat
from pathlib import Path
from urllib.parse import urlparse
from pilot_contracts import snapshot,runtime_fingerprint,validate_attestation
from preflight import inspect
from runtime_process import run_bounded


def capture(repo,profile,run_id,ttl_sec=300):
    if os.name!='posix' or not 0<ttl_sec<=900:raise ValueError('Linux capture and TTL <=900 seconds required')
    import pwd
    runtime_fingerprint(profile);snap=snapshot(repo)
    def cli_json(args):
        result=run_bounded(args,timeout=5)
        if result['timed_out'] or result['returncode']!=0:raise ValueError('Docker context metadata probe failed')
        return json.loads(result['stdout'])
    if os.environ.get('DOCKER_CONTEXT') or not os.environ.get('DOCKER_HOST'):
        endpoint=cli_json(['docker','context','inspect','--format','{{json .Endpoints.docker.Host}}'])
    else:endpoint=os.environ['DOCKER_HOST']
    parsed=urlparse(endpoint)
    if parsed.scheme!='unix' or parsed.netloc or parsed.query or parsed.fragment:raise ValueError('Selected endpoint is not a supported local Unix socket')
    if profile['mode']=='native-wsl' and parsed.path not in {'/var/run/docker.sock','/run/docker.sock'}:raise ValueError('Endpoint does not match native runtime profile')
    if profile['mode']=='scoped-relay' and (Path(parsed.path).name!='docker.sock' or Path(parsed.path).parent.parent!=Path('/tmp') or not Path(parsed.path).parent.name.startswith('vi-bench-proxy-')):raise ValueError('Endpoint does not match managed relay profile')
    preflight=inspect(Path('/tmp/vi-terminal-bench-runtime/jobs'),repo)
    if not preflight['ready']:return {'kind':'runtime-capture-failed','run_id':run_id,'snapshot_id':snap['id'],'preflight':preflight,'ready':False}
    observation={'user':pwd.getpwuid(os.getuid()).pw_name,'endpoint_class':profile['endpoint_class'],'docker_os':preflight['docker_os'],'filesystem_capabilities_ok':True,'verifier_network':'none','control_socket_in_sandbox':False,'endpoint':endpoint}
    if profile['mode']=='scoped-relay':
        info=Path(parsed.path).stat()
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid!=os.getuid():raise ValueError('Relay must be a socket owned by current ordinary user')
        # Observe managed wrapper ancestry without logging process arguments or credentials.
        pid=os.getppid();managed=False
        for _ in range(20):
            try:
                args=(Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
                managed|=any(arg.endswith(b'/scripts/with_runtime_proxy_v2.py') for arg in args)
                pid=int(next(line.split()[1] for line in (Path('/proc')/str(pid)/'status').read_text().splitlines() if line.startswith('PPid:')))
                if pid<=1:break
            except (OSError,StopIteration,ValueError):break
        if not managed:raise ValueError('Managed command-only wrapper ancestry not observed')
        observation.update(socket_mode=format(stat.S_IMODE(info.st_mode),'04o'),lifecycle='command-only',managed_wrapper_observed=True)
    now=dt.datetime.now(dt.timezone.utc)
    report={'schema':'vi-runtime-attestation/0.1','kind':'runtime-capture','run_id':run_id,'snapshot_id':snap['id'],'runtime_profile_id':profile['id'],'runtime_profile_sha256':runtime_fingerprint(profile),'issued_at_utc':now.isoformat(),'expires_at_utc':(now+dt.timedelta(seconds=ttl_sec)).isoformat(),'preflight':preflight,'observation':observation,'authorization_token':False}
    status,reason=validate_attestation(profile,report,run_id,snap['id'],now)
    report['ready']=status=='pass';report['validation_reason']=reason
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--profile',required=True);p.add_argument('--profiles',type=Path,required=True);p.add_argument('--run-id',required=True);p.add_argument('--ttl-sec',type=int,default=300);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Attestations are immutable; choose a fresh output path')
    options=json.loads(a.profiles.read_text(encoding='utf-8'))['profiles'];matches=[row for row in options if row['id']==a.profile]
    if len(matches)!=1:raise ValueError('Explicit known runtime profile required')
    try:report=capture(Path(__file__).resolve().parents[1],matches[0],a.run_id,a.ttl_sec)
    except (ValueError,OSError,KeyError,TypeError) as exc:report={'kind':'runtime-capture-failed','run_id':a.run_id,'ready':False,'error_type':type(exc).__name__,'reason':str(exc)}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"Runtime capture ready={report['ready']}; no fallback/root launcher used")
    raise SystemExit(0 if report['ready'] else 2)
