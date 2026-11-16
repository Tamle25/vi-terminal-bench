"""Loopback-only UI for the existing benchmark; no third-party packages required."""
import argparse
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timezone
import csv
import io
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
import uuid

ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).parent / 'static'
sys.path.insert(0, str(ROOT / 'scripts'))
from scoped_credentials import sanitize

ACTIONS = {'preview', 'check', 'smoke', 'batch', 'report', 'resume', 'status'}
ID = re.compile(r'[a-z0-9][a-z0-9-]{1,90}')
FILES = {'summary.json': 'application/json', 'normalized.jsonl': 'application/x-ndjson',
         'trials.csv': 'text/csv; charset=utf-8', 'results.md': 'text/markdown; charset=utf-8'}


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(sanitize(data), ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


@contextmanager
def instance_lock(path):
    """OS lock disappears on exit; never delete a stale lock to enable a retry."""
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open('a+b')
    try:
        stream.seek(0); stream.write(b'0'); stream.flush(); stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        stream.close()


def linux_path(path):
    if os.name != 'nt':
        return str(path.resolve())
    # Only used for paths under this checkout, not user-supplied paths.
    value = str(path.resolve()).replace('\\', '/')
    return '/mnt/' + value[0].lower() + value[2:]


def worker_command(action, run_id, target=None):
    worker = linux_path(ROOT / 'dashboard/worker.py')
    args = [action, '--run-id', run_id]
    if target:
        args += ['--target-run-id', target]
    if action == 'preview':
        # Pure Python preview works on Windows without Docker or WSL.
        return [sys.executable, '-u', str(ROOT / 'dashboard/worker.py'), *args]
    cfg = load(ROOT / 'configs/development-benchmark.json')
    python = cfg['state_root'] + '/venv/bin/python'
    if action == 'status' and os.name == 'nt':
        return ['wsl.exe', '-d', 'Ubuntu-22.04', '-u', 'tamle', '-e', python, '-u', worker, *args]
    relay = linux_path(ROOT / 'scripts/with_runtime_proxy_v2.py')
    if os.name == 'nt':
        return ['wsl.exe', '-d', 'Ubuntu-22.04', '-u', 'root', '-e', python, relay,
                '--user', 'tamle', '--timeout', '14400', '--', '/usr/bin/taskset', '-c', '0',
                python, '-u', worker, *args]
    return [python, '-u', worker, *args]


def historical():
    return {'id': 'stage11-development-001', 'name': 'Baseline · 6 tác vụ', 'origin': 'historical',
            'summary': load(ROOT / 'reports/development-benchmark-summary.json'),
            'trials': [json.loads(s) for s in (ROOT / 'reports/development-benchmark-trials.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]}


class Manager:
    def __init__(self, state=None, launcher=None):
        self.state = state or ROOT / '.dashboard'
        self.state.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.jobs = {}
        self.active = None
        self.launcher = launcher or subprocess.Popen
        for path in sorted((self.state / 'jobs').glob('*/job.json')):
            try:
                job = load(path)
                if not ID.fullmatch(job.get('id', '')):
                    continue
                if job.get('status') in {'queued', 'running'}:
                    job.update(status='interrupted', message='Dashboard đã khởi động lại. Kiểm tra trạng thái trước khi tiếp tục; không tự gửi lại request.')
                    atomic_json(path, job)
                self.jobs[job['id']] = job
            except (OSError, ValueError):
                continue

    def snapshot(self):
        with self.lock:
            return json.loads(json.dumps(sorted(self.jobs.values(), key=lambda j: j['created_at'], reverse=True)))

    def save(self, job):
        atomic_json(self.state / 'jobs' / job['id'] / 'job.json', job)

    def start(self, action, target_id=None):
        if action not in ACTIONS:
            raise ValueError('ACTION_NOT_ALLOWED')
        with self.lock:
            if self.active:
                raise RuntimeError('RUN_ALREADY_ACTIVE')
            target = None
            if action == 'resume':
                original = self.jobs.get(target_id)
                if not original or original['action'] not in {'smoke', 'batch'} or original['status'] not in {'failed', 'interrupted', 'incomplete'}:
                    raise ValueError('RESUME_TARGET_NOT_ALLOWED')
                target = original['run_id']
            jid = 'job-' + uuid.uuid4().hex[:12]
            run_id = 'dashboard-' + action + '-' + uuid.uuid4().hex[:12]
            job = {'id': jid, 'action': action, 'run_id': target or run_id, 'target_job_id': target_id,
                   'status': 'queued', 'created_at': now(), 'updated_at': now(), 'logs': [],
                   'message': 'Đang chuẩn bị', 'progress': None, 'summary': None, 'trials': [],
                   'provider_calls_allowed': action in {'smoke', 'batch', 'resume'}, 'exit_code': None}
            self.jobs[jid] = job; self.active = jid; self.save(job)
            threading.Thread(target=self._run, args=(jid, run_id, target), daemon=True).start()
            return dict(job)

    def _run(self, jid, run_id, target):
        job = self.jobs[jid]
        env = {k: v for k, v in os.environ.items() if not any(s in k.upper() for s in ['KEY', 'TOKEN', 'SECRET', 'PASSWORD'])}
        env.update(PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
        try:
            with self.lock:
                job.update(status='running', updated_at=now()); self.save(job)
            proc = self.launcher(worker_command(job['action'], run_id, target), cwd=str(ROOT),
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                 text=True, encoding='utf-8', errors='replace', env=env,
                                 **({'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}))
            for line in proc.stdout:
                line = sanitize(line.rstrip().replace('\x00', ''))[:1048576]
                with self.lock:
                    if line.startswith('@@DASHBOARD '):
                        try:
                            event = json.loads(line[len('@@DASHBOARD '):])
                            if event.get('type') == 'bundle':
                                job['summary'] = event['summary']; job['trials'] = event['trials']
                                self.export(job)
                            elif event.get('type') == 'progress':
                                job['progress'] = event['progress']
                            elif event.get('type') == 'message':
                                job['message'] = str(event['message'])
                                job['logs'].append(str(event['message']))
                            elif event.get('type') == 'runtime':
                                job['runtime'] = event['runtime']
                            elif event.get('type') == 'runtime_policy':
                                job['runtime_policy'] = event['runtime_policy']
                                job['logs'].append('Runtime clock: CLOCK_BOOTTIME; hạn attestation 15 phút được giữ nguyên. Đã lưu version/hash của bản sửa runtime.')
                            elif event.get('type') == 'ledger':
                                job['ledger'] = event['ledger']; job['ledger_checked_at'] = now()
                            elif event.get('type') == 'error':
                                job['error_code'] = str(event.get('code', 'WORKER_FAILED'))
                                job['message'] = str(event.get('message', 'Lần chạy đã dừng.'))
                        except (ValueError, KeyError):
                            job['logs'].append('WORKER_EVENT_INVALID')
                    elif line:
                        job['logs'].append(line[:12000])
                        try:
                            progress = json.loads(line)
                            if 'progress' in progress:
                                job['progress'] = progress
                        except ValueError:
                            pass
                    job['logs'] = job['logs'][-400:]
                    job['updated_at'] = now(); self.save(job)
            code = proc.wait()
            with self.lock:
                complete = job.get('summary', {}).get('complete', False) if job.get('summary') else None
                job.update(exit_code=code, status='completed' if code == 0 else ('incomplete' if code == 3 else 'failed'), updated_at=now())
                if code == 0:
                    job['message'] = 'Đã hoàn tất' if complete is not False else 'Đã xuất báo cáo; vẫn còn lượt chưa hoàn tất'
                elif not job.get('error_code'):
                    job['message'] = 'Lần chạy đã dừng. Xem nhật ký; không tự chạy lại trial chưa rõ trạng thái.'
        except Exception:
            with self.lock:
                job.update(status='failed', error_code='WORKER_START_FAILED',
                           message='Chưa khởi chạy được. Kiểm tra WSL, Docker Desktop và Python theo hướng dẫn.', updated_at=now())
        finally:
            with self.lock:
                self.save(job); self.active = None

    def export(self, job):
        folder = self.state / 'jobs' / job['id'] / 'files'; folder.mkdir(parents=True, exist_ok=True)
        atomic_json(folder / 'summary.json', job['summary'])
        (folder / 'normalized.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in job['trials']), encoding='utf-8')
        fields = ['trial_id', 'task_id', 'language', 'repeat', 'status', 'reward', 'valid', 'duration_sec', 'input_tokens', 'output_tokens', 'cost_usd']
        with (folder / 'trials.csv').open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fields, extrasaction='ignore'); writer.writeheader(); writer.writerows(job['trials'])
        (folder / 'results.md').write_text('# Development benchmark\n\n' + json.dumps(job['summary'], ensure_ascii=False, indent=2), encoding='utf-8')


class Handler(BaseHTTPRequestHandler):
    server_version = 'ViBenchDashboard'

    def log_message(self, *_):
        pass

    def reply(self, code, data, mime='application/json; charset=utf-8', download=None):
        if not isinstance(data, bytes):
            data = json.dumps(sanitize(data), ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        for key, val in {'Content-Type': mime, 'Content-Length': str(len(data)), 'Cache-Control': 'no-store',
                         'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY', 'Referrer-Policy': 'no-referrer',
                         'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}.items():
            self.send_header(key, val)
        if download:
            self.send_header('Content-Disposition', 'attachment; filename="' + download + '"')
        self.end_headers(); self.wfile.write(data)

    def allowed_host(self):
        return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}

    def do_GET(self):
        if not self.allowed_host():
            return self.reply(403, {'error': 'HOST_DENIED'})
        path = urlsplit(self.path).path
        if path == '/api/state':
            cfg = load(ROOT / 'configs/development-benchmark.json')
            return self.reply(200, {'baseline': historical(), 'jobs': self.server.manager.snapshot(),
                'config': {k: cfg[k] for k in ['model', 'configuration', 'pool_cap_usd', 'max_requests_per_trial', 'trial_timeout_sec', 'reasoning']},
                'tasks': [json.loads(s) for s in (ROOT / 'manifest.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()],
                'budget': load(ROOT / 'reports/stage11-summary.json')['budget'],
                'credential_file_present': (ROOT / '.env').is_file(), 'session_token': self.server.token})
        if path == '/api/health':
            return self.reply(200, {'ok': True, 'mode': 'local', 'read_only': self.server.read_only,
                                    'model_calls_by_health_check': 0})
        if path.startswith('/downloads/'):
            pieces = path.split('/')
            if len(pieces) != 4 or pieces[3] not in FILES:
                return self.reply(404, {'error': 'NOT_FOUND'})
            jid, name = pieces[2:]
            if jid == 'baseline':
                names = {'summary.json': 'development-benchmark-summary.json', 'trials.csv': 'development-benchmark-trials.csv',
                         'normalized.jsonl': 'development-benchmark-trials.jsonl', 'results.md': 'development-benchmark-results.md'}
                file = ROOT / 'reports' / names[name]
            elif ID.fullmatch(jid) and jid in self.server.manager.jobs:
                file = self.server.manager.state / 'jobs' / jid / 'files' / name
            else:
                return self.reply(404, {'error': 'NOT_FOUND'})
            if file.is_file():
                return self.reply(200, file.read_bytes(), FILES[name], name)
            return self.reply(404, {'error': 'REPORT_NOT_READY'})
        assets = {'/': ('index.html', 'text/html; charset=utf-8'), '/index.html': ('index.html', 'text/html; charset=utf-8'),
                  '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8'),
                  '/favicon.svg': ('favicon.svg', 'image/svg+xml')}
        if path in assets:
            name, mime = assets[path]
            return self.reply(200, (STATIC / name).read_bytes(), mime)
        self.reply(404, {'error': 'NOT_FOUND'})

    def do_POST(self):
        if not self.allowed_host():
            return self.reply(403, {'error': 'HOST_DENIED'})
        origin = self.headers.get('Origin')
        allowed = {f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'}
        if origin not in allowed or not secrets.compare_digest(self.headers.get('X-Dashboard-Token', ''), self.server.token):
            return self.reply(403, {'error': 'ORIGIN_OR_TOKEN_DENIED'})
        if urlsplit(self.path).path != '/api/jobs':
            return self.reply(404, {'error': 'NOT_FOUND'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 2048 or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('INVALID_BODY')
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict) or set(data) - {'action', 'target_job_id'} or not isinstance(data.get('action'), str):
                raise ValueError('INVALID_BODY')
            if data.get('target_job_id') is not None and not isinstance(data['target_job_id'], str):
                raise ValueError('INVALID_BODY')
            if getattr(self.server, 'read_only', False) and data['action'] in {'smoke', 'batch', 'resume'}:
                return self.reply(403, {'error': 'MODEL_DISABLED_FOR_QA'})
            result = self.server.manager.start(data['action'], data.get('target_job_id'))
            return self.reply(202, result)
        except RuntimeError:
            return self.reply(409, {'error': 'RUN_ALREADY_ACTIVE'})
        except (ValueError, TypeError):
            return self.reply(400, {'error': 'INVALID_ACTION_OR_BODY'})


def make_server(port=8765, state=None, launcher=None, read_only=False):
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.manager = Manager(state, launcher)
    server.token = secrets.token_urlsafe(32)
    server.read_only = read_only
    return server


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--read-only', action='store_true', help='Reject paid actions during browser QA')
    args = parser.parse_args()
    with instance_lock(ROOT / '.dashboard/server.lock'):
        state = ROOT / '.dashboard' / ('qa' if args.read_only else 'runtime')
        server = make_server(args.port, state=state, read_only=args.read_only)
        print(f'Dashboard: http://127.0.0.1:{server.server_port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == '__main__':
    main()
