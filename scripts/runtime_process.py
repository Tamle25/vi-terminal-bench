"""Bounded, owned subprocess groups; file-backed capture avoids inherited-pipe hangs."""
import os
import signal
import subprocess
import tempfile
import time


def _stop_group(process):
    if os.name == 'posix':
        try: os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError: pass
        try: process.wait(timeout=.5)
        except subprocess.TimeoutExpired: pass
        try: os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError: pass
    elif process.poll() is None:
        process.kill()
    try: process.wait(timeout=1)
    except subprocess.TimeoutExpired: pass


def run_bounded(command, timeout=10, capture=True, cwd=None, log_path=None):
    if timeout <= 0: raise ValueError('Probe deadline exhausted')
    started=time.monotonic()
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            process=subprocess.Popen(command,stdout=stdout,stderr=stderr,cwd=cwd,start_new_session=os.name=='posix')
        except OSError as exc:
            return dict(returncode=None,timed_out=False,elapsed_sec=time.monotonic()-started,error_type=type(exc).__name__,stdout='',stderr=str(exc))
        timed_out=False
        try: process.wait(timeout=timeout)
        except subprocess.TimeoutExpired: timed_out=True
        finally: _stop_group(process)
        stdout.seek(0);stderr.seek(0)
        out=stdout.read(65536);err=stderr.read(65536)
        if log_path is not None:
            log_path.parent.mkdir(parents=True,exist_ok=True)
            stdout.seek(0);stderr.seek(0)
            with log_path.open('wb') as target:
                while chunk:=stdout.read(65536): target.write(chunk)
                target.write(b'\n--- stderr ---\n')
                while chunk:=stderr.read(65536): target.write(chunk)
        return dict(returncode=process.returncode,timed_out=timed_out,elapsed_sec=time.monotonic()-started,stdout=out.decode('utf-8',errors='replace') if capture else '',stderr=err.decode('utf-8',errors='replace') if capture else '')
