import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from dashboard import server


class FakeProcess:
    def __init__(self, lines, code=0):
        self.stdout = io.StringIO('\n'.join(lines) + '\n'); self.code = code

    def wait(self):
        return self.code


def wait_job(manager, jid):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        with manager.lock:
            if manager.jobs[jid]['status'] not in {'queued', 'running'}:
                return manager.jobs[jid]
        time.sleep(.01)
    raise AssertionError('Job did not finish')


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_large_real_result_event_survives_and_csv_has_bom(self):
        rows = [{'trial_id': str(i), 'status': 'completed', 'valid': True, 'reward': i % 2,
                 'artifact_sha256': {'a': 'a' * 600}, 'task_id': 'b001-vn-invoice'} for i in range(36)]
        event = '@@DASHBOARD ' + json.dumps({'type':'bundle', 'summary':{'complete':True}, 'trials':rows})
        self.assertGreater(len(event), 12000)
        manager = server.Manager(self.root, lambda *a, **k: FakeProcess([event]))
        job = wait_job(manager, manager.start('smoke')['id'])
        self.assertEqual(job['status'], 'completed'); self.assertEqual(job['trials'], rows)
        self.assertTrue((self.root/'jobs'/job['id']/'files/trials.csv').read_bytes().startswith(b'\xef\xbb\xbf'))
        restored = server.Manager(self.root)
        self.assertEqual(restored.jobs[job['id']]['trials'], rows)

    def test_no_shell_or_credentials_forwarded_to_worker(self):
        captured = {}
        def launch(args, **kwargs):
            captured.update(args=args, **kwargs)
            return FakeProcess([])
        old = os.environ.get('OPENAI_API_KEY'); os.environ['OPENAI_API_KEY'] = 'unit-fixture-do-not-forward'
        try:
            manager = server.Manager(self.root, launch)
            wait_job(manager, manager.start('preview')['id'])
        finally:
            if old is None: os.environ.pop('OPENAI_API_KEY', None)
            else: os.environ['OPENAI_API_KEY'] = old
        self.assertNotIn('OPENAI_API_KEY', captured['env'])
        self.assertNotIn('shell', captured)
        self.assertTrue(all('unit-fixture' not in arg for arg in captured['args']))

    def test_active_job_and_untrusted_actions_rejected(self):
        manager = server.Manager(self.root)
        manager.active = 'existing'
        with self.assertRaises(RuntimeError): manager.start('batch')
        manager.active = None
        with self.assertRaises(ValueError): manager.start('rm -rf')
        with self.assertRaises(ValueError): manager.start('resume', '../other')

    def test_restart_marks_running_as_interrupted_without_replay(self):
        jid = 'job-123456789abc'
        server.atomic_json(self.root/'jobs'/jid/'job.json', {'id':jid, 'status':'running', 'created_at':'2026-11-13'})
        manager = server.Manager(self.root, lambda *a, **k: self.fail('Must never replay'))
        self.assertEqual(manager.jobs[jid]['status'], 'interrupted')
        self.assertIsNone(manager.active)

    def test_preview_executes_without_model_or_linux(self):
        proc = subprocess.run([sys.executable, str(server.ROOT/'dashboard/worker.py'), 'preview',
                               '--run-id', 'dashboard-smoke-123456789abc'], capture_output=True, env={**os.environ,'PYTHONUTF8':'1'}, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        events = [json.loads(s.split(' ',1)[1]) for s in proc.stdout.decode('utf-8').splitlines()]
        runtime = next(e['runtime'] for e in events if e['type']=='runtime')
        self.assertEqual(runtime['provider_calls'], 0); self.assertFalse(runtime['credential_read'])
        self.assertEqual(runtime['planned_trials'],36)

    def test_frozen_cli_sources_and_public_inputs_unchanged(self):
        from development_contracts import sources, public_inputs
        plan = server.load(server.ROOT/'reports/stage11-batch-plan.json')
        checked = server.load(server.ROOT/'reports/stage11-unit-tests-handoff.json')
        self.assertEqual(sources(server.ROOT), plan['source_sha256'])
        self.assertEqual(public_inputs(server.ROOT), checked['input_sha256'])

    def test_budget_inspection_never_mutates_ledger(self):
        import hashlib
        from development_ledger import DevelopmentLedger
        from dashboard.worker import readonly_ledger
        dbpath = self.root / 'ledger.sqlite3'
        ledger = DevelopmentLedger(dbpath, account='dashboard-test', pool_cap=2000000000, origin='real')
        ledger.add_margin(); expected = ledger.inspect(); ledger.close()
        before = hashlib.sha256(dbpath.read_bytes()).hexdigest()
        cfg = {'state_root':str(self.root), 'account_reference':'dashboard-test','pool_cap_usd':'2'}
        self.assertEqual(readonly_ledger(cfg), expected)
        self.assertEqual(hashlib.sha256(dbpath.read_bytes()).hexdigest(), before)
        with self.assertRaises(ValueError): readonly_ledger({**cfg, 'account_reference':'wrong'})

    def test_resume_preserves_original_run_identity(self):
        manager = server.Manager(self.root, lambda *a, **k: FakeProcess([]))
        original = {'id':'job-123456789abc', 'run_id':'dashboard-smoke-123456789abc', 'action':'smoke', 'status':'failed', 'created_at':server.now()}
        manager.jobs[original['id']] = original
        resumed = wait_job(manager, manager.start('resume', original['id'])['id'])
        self.assertEqual(resumed['run_id'], original['run_id'])
        self.assertEqual(resumed['target_job_id'], original['id'])


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = server.make_server(0, Path(self.tmp.name), lambda *a, **k: FakeProcess([]), read_only=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(); self.tmp.cleanup()

    def request(self, path, body=None, **headers):
        req = Request(self.base+path, data=None if body is None else json.dumps(body).encode(), headers=headers)
        try:
            with urlopen(req, timeout=5) as response: return response.status, response.read(), response.headers
        except HTTPError as error: return error.code, error.read(), error.headers

    def post(self, body):
        return self.request('/api/jobs',body,Origin=self.base, **{'X-Dashboard-Token':self.server.token,'Content-Type':'application/json'})

    def test_state_real_baseline_and_private_paths_not_served(self):
        code, body, headers = self.request('/api/state'); data=json.loads(body)
        self.assertEqual(code,200); self.assertEqual(data['baseline']['summary']['valid_trials'],36)
        self.assertEqual(sum(r['reward'] for r in data['baseline']['trials']),35)
        self.assertNotIn('OPENAI_API_KEY', body.decode()); self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
        for path in ['/.env','/../.env','/scripts/scoped_credentials.py','/downloads/baseline/.env','/api/arbitrary']:
            self.assertEqual(self.request(path)[0],404,path)

    def test_host_origin_token_and_read_only_guards(self):
        self.assertEqual(self.request('/api/state',Host='evil.example')[0],403)
        self.assertEqual(self.request('/api/jobs',{'action':'preview'},**{'Content-Type':'application/json'})[0],403)
        self.assertEqual(self.post({'action':'smoke'})[0],403)
        self.assertEqual(self.post({'action':'batch'})[0],403)
        self.assertEqual(self.post({'action':'preview','command':'echo injected'})[0],400)
        self.assertEqual(self.post({'action':'not-an-action'})[0],400)
        self.assertEqual(self.post({'action':'preview'})[0],202)

    def test_export_and_utf8_html(self):
        code,body,_=self.request('/');self.assertEqual(code,200)
        self.assertIn('Tổng quan benchmark',body.decode('utf-8'))
        code,body,headers=self.request('/downloads/baseline/trials.csv')
        self.assertEqual(code,200);self.assertTrue(body.startswith(b'\xef\xbb\xbf'))
        self.assertIn('attachment',headers['Content-Disposition'])


if __name__ == '__main__':
    unittest.main()
