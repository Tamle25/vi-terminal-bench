"""Owned Docker sandbox only. Model commands are argv data, never host shell code."""
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import subprocess
import tarfile
import threading


def bounded(command, timeout, limit=65536):
    # Separate draining threads prevent pipe deadlock; retained output is bounded.
    env = {k: os.environ[k] for k in ['PATH', 'HOME', 'USER', 'SYSTEMROOT', 'TEMP', 'TMP', 'DOCKER_HOST', 'DOCKER_CONTEXT'] if k in os.environ}
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               env=env, start_new_session=os.name == 'posix')
    buffers = [bytearray(), bytearray()]; truncated = [False, False]
    def drain(stream, index):
        with stream:
            while chunk := stream.read(4096):
                remaining = max(0, limit-len(buffers[index]))
                buffers[index].extend(chunk[:remaining])
                truncated[index] |= len(chunk) > remaining
    threads = [threading.Thread(target=drain, args=(stream, i), daemon=True)
               for i, stream in enumerate([process.stdout, process.stderr])]
    for thread in threads: thread.start()
    timed_out = False
    try: process.wait(timeout=timeout)
    except subprocess.TimeoutExpired: timed_out = True
    finally:
        # Also stop descendants which can retain capture pipes after parent exits.
        if os.name == 'posix':
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
        elif process.poll() is None: process.kill()
        process.wait()
    for thread in threads: thread.join(timeout=2)
    if any(thread.is_alive() for thread in threads): raise ValueError('CAPTURE_PIPE_UNCLOSED')
    return {'exit_code': process.returncode, 'timed_out': timed_out,
            'stdout_bytes': bytes(buffers[0]), 'stderr_bytes': bytes(buffers[1]), 'truncated': truncated}


def extract_data(raw, target, max_bytes=16777216):
    """Validate the whole archive before creating files; never extract link/devices."""
    target = Path(target)
    if target.exists(): raise ValueError('ARTIFACT_DESTINATION_EXISTS')
    files = []; seen = set(); total = 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            if (name.is_absolute() or '..' in name.parts or '\\' in member.name
                    or not (member.isdir() or member.isfile()) or str(name) in seen):
                raise ValueError('UNSAFE_ARTIFACT_ARCHIVE')
            seen.add(str(name))
            if len(seen) > 4096: raise ValueError('ARTIFACT_FILE_COUNT')
            if member.isfile():
                total += member.size
                if member.size < 0 or total > max_bytes: raise ValueError('ARTIFACT_SIZE')
                content = archive.extractfile(member).read(member.size+1)
                if len(content) != member.size: raise ValueError('ARTIFACT_SIZE')
                files.append((name, content))
    # New tree prevents overwriting existing symlinks; parents checked for each file.
    if any(p.is_symlink() for p in [target, *target.parents]): raise ValueError('ARTIFACT_DESTINATION_SYMLINK')
    target.mkdir(parents=True)
    for name, content in files:
        path = target.joinpath(*name.parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.resolve().is_relative_to(target.resolve()): raise ValueError('ARTIFACT_ESCAPE')
        with path.open('xb') as output: output.write(content)


WRAPPER = '''import os, signal, subprocess, sys, tempfile, json
with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
 p = subprocess.Popen(['/bin/bash','-c',sys.argv[1]], stdout=out, stderr=err, start_new_session=True)
 timeout = False
 try: p.wait(timeout=float(sys.argv[2]))
 except subprocess.TimeoutExpired: timeout = True
 finally:
  try: os.killpg(p.pid,signal.SIGKILL)
  except ProcessLookupError: pass
  p.wait()
 limit=int(sys.argv[3]); out.seek(0); err.seek(0)
 a=out.read(limit+1); b=err.read(limit+1)
 print(json.dumps({'exit_code':p.returncode,'timed_out':timeout,'stdout':a[:limit].decode('utf-8',errors='replace'),'stderr':b[:limit].decode('utf-8',errors='replace'),'stdout_truncated':len(a)>limit,'stderr_truncated':len(b)>limit},ensure_ascii=False))
'''


class DockerSandbox:
    origin = 'docker-sandbox'

    def __init__(self, cid, run, image_id, config, cli='docker'):
        if not re.fullmatch('[0-9a-f]{64}', cid) or not re.fullmatch('sha256:[0-9a-f]{64}', image_id):
            raise ValueError('IMMUTABLE_CONTAINER_ID_REQUIRED')
        self.cid, self.run, self.image_id, self.config, self.cli = cid, run, image_id, config, cli
        self.poisoned = False

    def inspect(self):
        if self.poisoned: raise ValueError('SANDBOX_POISONED')
        result = bounded([self.cli, 'inspect', self.cid], 5)
        if result['exit_code'] != 0 or result['timed_out']: raise ValueError('SANDBOX_INSPECT_FAILED')
        rows = json.loads(result['stdout_bytes'])
        if len(rows) != 1: raise ValueError('SANDBOX_IDENTITY')
        row = rows[0]; host = row['HostConfig']; cfg = row['Config']
        bad_env = any(entry.split('=',1)[0].upper().endswith(('API_KEY','TOKEN','SECRET')) for entry in cfg.get('Env', []))
        if (row['Id'] != self.cid or row['Image'] != self.image_id or not row['State']['Running']
                or cfg.get('Labels', {}).get('vi-bench.run') != self.run
                or host['NetworkMode'] != 'none' or host.get('Privileged') or host.get('Binds')
                or host.get('PidMode') == 'host' or host.get('IpcMode') == 'host'
                or host.get('CapAdd') or 'ALL' not in host.get('CapDrop', [])
                or 'no-new-privileges' not in host.get('SecurityOpt', [])
                or not host.get('ReadonlyRootfs') or host.get('Devices') or bad_env
                or host.get('NanoCpus') != self.config['cpus']*1000000000
                or host.get('Memory') != self.config['memory_mb']*1048576
                or host.get('PidsLimit') != self.config['pids_limit']
                or set(host.get('Tmpfs', {})) != {'/tmp','/app/output'}
                or any(v != 'rw,nosuid,nodev,size=16m' for v in host.get('Tmpfs', {}).values())
                or cfg.get('Cmd')!=['sleep','360']
                or any(m['Type'] != 'tmpfs' for m in row.get('Mounts', []))):
            raise ValueError('SANDBOX_POLICY_MISMATCH')
        return {'origin': self.origin, 'container_id': self.cid, 'image_id': self.image_id,
                'network': 'none', 'no_host_mounts': True, 'readonly_rootfs': True}

    def command(self, command, timeout):
        self.inspect()
        if not isinstance(command, str) or not command or '\0' in command or len(command.encode('utf-8')) > self.config['max_command_bytes']:
            raise ValueError('COMMAND_SCHEMA')
        timeout = min(timeout, self.config['command_timeout_sec'])
        if timeout <= 0: raise ValueError('TRIAL_DEADLINE')
        result = bounded([self.cli, 'exec', '-w', '/app', self.cid, 'python', '-I', '-c', WRAPPER,
                          command, str(timeout), str(self.config['command_output_bytes'])], timeout+3,
                         self.config['command_output_bytes']*12+4096)
        if result['timed_out'] or result['exit_code'] != 0 or any(result['truncated']):
            self.poisoned = True
            # Stop only the container whose immutable identity/policy was checked.
            bounded([self.cli, 'kill', self.cid], 5)
            raise ValueError('TERMINAL_INFRA_FAILURE')
        return json.loads(result['stdout_bytes'])

    def collect(self, target):
        self.inspect()
        # Freeze writers before transfer. This sandbox is one-use, never restarted.
        # Pause, rather than stop: tmpfs output must remain mounted during copy.
        result = bounded([self.cli, 'pause', self.cid], 5)
        if result['exit_code'] != 0 or result['timed_out']: raise ValueError('SANDBOX_PAUSE_FAILED')
        self.poisoned = True
        result = bounded([self.cli, 'cp', self.cid + ':/app/.', '-'], 10, self.config['artifact_max_bytes']+1048576)
        if result['exit_code'] != 0 or result['timed_out'] or result['truncated'][0]: raise ValueError('ARTIFACT_TRANSFER_FAILED')
        extract_data(result['stdout_bytes'], target, self.config['artifact_max_bytes'])

    def destroy(self):
        # Cleanup verifies ownership again, including after a poisoned/paused state.
        observed = bounded([self.cli, 'inspect', self.cid], 5)
        if observed['exit_code'] != 0 or observed['timed_out']: raise ValueError('CLEANUP_IDENTITY_UNVERIFIED')
        row = json.loads(observed['stdout_bytes'])[0]
        if row['Id'] != self.cid or row['Config'].get('Labels', {}).get('vi-bench.run') != self.run:
            raise ValueError('CLEANUP_IDENTITY_UNVERIFIED')
        result = bounded([self.cli, 'rm', '-f', self.cid], 5)
        if result['exit_code'] != 0 or result['timed_out']: raise ValueError('CLEANUP_FAILED')

    @staticmethod
    def create_args(image_id, run, config):
        if not re.fullmatch('sha256:[0-9a-f]{64}', image_id): raise ValueError('IMAGE_ID_REQUIRED')
        return ['docker', 'create', '--label', 'vi-bench.run='+run, '--network', 'none', '--read-only',
                '--tmpfs', '/tmp:rw,nosuid,nodev,size=16m', '--tmpfs', '/app/output:rw,nosuid,nodev,size=16m',
                '--cpus', str(config['cpus']), '--memory', str(config['memory_mb'])+'m',
                '--pids-limit', str(config['pids_limit']), '--cap-drop', 'ALL',
                '--security-opt', 'no-new-privileges', image_id, 'sleep', '360']
