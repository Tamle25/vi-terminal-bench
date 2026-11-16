"""Ephemeral local Unix relay; run a command as the original user, then remove it.

Requires WSL root only to reach Docker Desktop's protected distro proxy. Never
changes /run/docker.sock, Docker config, group membership, or shared services.
"""
import argparse
import asyncio
import os
import pwd
import shutil
import signal
import tempfile
from pathlib import Path


async def execute(user,command,timeout):
    if os.geteuid()!=0:raise ValueError('Scoped relay requires WSL root')
    account=pwd.getpwnam(user)
    if account.pw_uid==0:raise ValueError('Run target must be an ordinary user')
    upstream='/mnt/wsl/docker-desktop/shared-sockets/guest-services/docker.container-proxy.sock'
    if not Path(upstream).is_socket():raise ValueError('Expected Docker Desktop distro proxy missing')
    directory=Path(tempfile.mkdtemp(prefix='vi-bench-proxy-',dir='/tmp'));directory.chmod(0o711)
    local=directory/'docker.sock';connections=set()
    async def relay(reader,writer):
        task=asyncio.current_task();connections.add(task);remote=None
        try:
            remote_reader,remote=await asyncio.wait_for(asyncio.open_unix_connection(upstream),5)
            async def copy(source,target):
                while chunk:=await source.read(65536):target.write(chunk);await target.drain()
                if target.can_write_eof():target.write_eof()
            await asyncio.gather(copy(reader,remote),copy(remote_reader,writer))
        except (OSError,asyncio.TimeoutError,ConnectionError):pass
        finally:
            writer.close()
            if remote:remote.close()
            connections.discard(task)
    server=await asyncio.start_unix_server(relay,path=str(local))
    local.chmod(0o600);os.chown(local,account.pw_uid,account.pw_gid)
    environment=dict(os.environ);environment.pop('DOCKER_CONTEXT',None);environment['DOCKER_HOST']='unix://'+str(local)
    process=None
    try:
        process=await asyncio.create_subprocess_exec('runuser','-u',user,'--',*command,env=environment,start_new_session=True)
        try:return await asyncio.wait_for(process.wait(),timeout)
        except asyncio.TimeoutError:
            os.killpg(process.pid,signal.SIGTERM)
            try:await asyncio.wait_for(process.wait(),2)
            except asyncio.TimeoutError:os.killpg(process.pid,signal.SIGKILL);await process.wait()
            return 124
    finally:
        server.close();await server.wait_closed()
        for task in list(connections):task.cancel()
        await asyncio.gather(*list(connections),return_exceptions=True)
        local.unlink(missing_ok=True);directory.rmdir()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--user',required=True);p.add_argument('--timeout',type=float,default=900);p.add_argument('command',nargs=argparse.REMAINDER)
    args=p.parse_args();command=args.command[1:] if args.command[:1]==['--'] else args.command
    if not command:raise ValueError('Command required')
    raise SystemExit(asyncio.run(execute(args.user,command,args.timeout)))
