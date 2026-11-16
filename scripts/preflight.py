"""Fail before execution when filesystem, runtime, or static network policy is unsuitable."""
import argparse
import json
import platform
import subprocess
import tempfile
import unicodedata
import time
from pathlib import Path
from runtime_process import run_bounded


def filesystem_probe(path):
    resolved=path.resolve()
    if platform.system()!='Linux' or str(resolved).startswith('/mnt/'):
        raise ValueError('Jobs require native Linux storage, not a Windows mount')
    resolved.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='vi-preflight-',dir=resolved) as folder:
        root=Path(folder)
        names=['Case.txt','case.txt','Báo cáo.txt',unicodedata.normalize('NFD','Báo cáo.txt')]
        for index,name in enumerate(names):
            (root/name).write_bytes(str(index).encode('ascii'))
        if {p.name for p in root.iterdir()}!=set(names):
            raise ValueError('Filesystem loses case/Unicode distinctions')
        if [(root/name).read_bytes() for name in names]!=[str(i).encode('ascii') for i in range(4)]:
            raise ValueError('Filesystem merged file contents')
    return str(resolved)


def inspect(jobs,repo,deadline_sec=45,runner=run_bounded):
    started=time.monotonic();steps=[];values={};failed=None
    def step(name,function):
        before=time.monotonic()
        if before-started>=deadline_sec:raise ValueError('Preflight total deadline exceeded')
        try:
            value=function()
            steps.append(dict(name=name,passed=True,elapsed_sec=time.monotonic()-before))
            return value
        except (ValueError,OSError,subprocess.SubprocessError,KeyError,TypeError) as exc:
            steps.append(dict(name=name,passed=False,error_type=type(exc).__name__,detail=str(exc),elapsed_sec=time.monotonic()-before))
            raise ValueError(name+' failed') from exc
    def command(args,limit):
        result=runner(args,timeout=min(limit,max(.01,deadline_sec-(time.monotonic()-started))))
        if result['timed_out']:raise ValueError('Owned CLI probe timed out; process group stopped')
        if result['returncode']!=0:raise ValueError('CLI returned nonzero: '+result['stderr'][:500])
        return result['stdout']
    try:
        native=step('filesystem-capabilities',lambda:filesystem_probe(jobs));values['jobs_dir']=native
        values['filesystem_type']=step('filesystem-type',lambda:command(['stat','-f','-c','%T',native],5).strip())
        version=step('docker-cli-engine',lambda:json.loads(command(['docker','version','--format','{{json .Server}}'],10)))
        step('docker-linux',lambda:True if version['Os']=='linux' else (_ for _ in ()).throw(ValueError('Docker Linux required')))
        values.update(docker_server=version['Version'],docker_os=version['Os'])
        def policy():
            rows=[json.loads(line) for line in (repo/'manifest.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
            for row in rows:
                for phase in ['environment','tests']:
                    compose=repo/'tasks'/row['task_id']/phase/'docker-compose.yaml'
                    if compose.read_text(encoding='utf-8')!='services:\n  main:\n    network_mode: none\n':raise ValueError('Static network policy drift')
            return len(rows)
        values['tasks']=step('static-network-policy',policy);values['static_network_none']=True
    except ValueError as exc:failed=str(exc)
    return dict(ready=failed is None,steps=steps,elapsed_sec=time.monotonic()-started,deadline_sec=deadline_sec,error=failed,**values)


def check(jobs,repo):
    report=inspect(jobs,repo)
    if not report['ready']:raise ValueError(json.dumps(report,ensure_ascii=False))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--jobs-dir',type=Path,required=True);p.add_argument('--output',type=Path)
    args=p.parse_args()
    try:
        report=inspect(args.jobs_dir,Path(__file__).resolve().parents[1])
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        report={'ready':False,'error_type':type(exc).__name__,'detail':str(exc),'jobs_dir':str(args.jobs_dir)}
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
    raise SystemExit(0 if report['ready'] else 2)
