"""Inspect only Docker Desktop's known local sockets; read-only /version probes."""
import argparse
import json
import time
from pathlib import Path
from diagnose_runtime import UnixConnection


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    candidates=[Path('/var/run/docker.sock')]
    for directory in ['host-services','guest-services']:
        root=Path('/mnt/wsl/docker-desktop/shared-sockets')/directory
        if root.exists():candidates.extend(path for path in root.glob('*docker*.sock') if path not in candidates)
    rows=[]
    for path in candidates[:6]:
        started=time.monotonic();conn=UnixConnection('localhost',timeout=2)
        # Use a dedicated connection class so no Docker config/credentials are loaded.
        import socket
        def connect(connection=conn,target=str(path)):
            connection.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            connection.sock.settimeout(2);connection.sock.connect(target)
        conn.connect=connect
        row={'path':str(path),'resolved':str(path.resolve()),'exists':path.exists()}
        try:
            conn.request('GET','/version',headers={'Connection':'close'});response=conn.getresponse();data=json.loads(response.read(65536))
            row.update(status=response.status,version=data.get('Version'),os=data.get('Os'))
        except Exception as exc:row['error_type']=type(exc).__name__
        finally:conn.close()
        row['elapsed_sec']=time.monotonic()-started;rows.append(row)
    args.output.write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8');print(json.dumps(rows))
