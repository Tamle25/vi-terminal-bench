import copy
import datetime as dt
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aggregate_results import aggregate
from execution_contracts import assess, build_manifest, validate_manifest
from executor_fixtures import fixture, write_json
from model_executor import Executor, FixtureAdapter, load_json
from pilot_contracts import snapshot
from pilot_runner import FakeProvider, SimulatedCrash, export
from review_records import validate_reviews

REPO = Path(__file__).resolve().parents[2]


class Clock:
    def __init__(self): self.value = time.time()
    def __call__(self): return self.value
    def advance(self, seconds=31): self.value += seconds


def receipt(status='completed', reward=1, i=1000, c=100):
    return {'status': status, 'reward': reward, 'inference_micros': i, 'compute_micros': c}


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        (REPO / 'build').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=REPO / 'build')
        self.root = Path(self.temp.name)
        self.clock = Clock()
        self.context, self.manifest = fixture(REPO, self.root, now=dt.datetime.fromtimestamp(self.clock(), dt.timezone.utc))
        self.handles = []

    def tearDown(self):
        for item in reversed(self.handles):
            if isinstance(item, Executor): item.close()
            else: item.db.close()
        self.temp.cleanup()

    def executor(self, scenarios=None):
        provider = FakeProvider(self.root / 'state/fake-provider.sqlite3', scenarios)
        adapter = FixtureAdapter(provider, self.root / 'effective-settings.json')
        executor = Executor(REPO, lambda: load_json(self.root / 'context.json'), self.manifest, adapter, self.root / 'state', self.clock)
        self.handles.extend([provider, executor])
        return executor, provider

    def save(self): write_json(self.root / 'context.json', self.context)

    def assess(self, executor, mode='offline-fixture'):
        return assess(REPO, self.context, self.manifest, executor.adapter.inspect(REPO, self.manifest), mode, dt.datetime.fromtimestamp(self.clock(), dt.timezone.utc))

    def two_requests(self):
        self.context, self.manifest = fixture(REPO, self.root, requests=2, now=dt.datetime.fromtimestamp(self.clock(), dt.timezone.utc))
        # Bound 2 x 1000 / 100, rather than fixture helper's looser attempt estimate.
        self.context['budget_evidence']['reservation'] = {'inference': 2000, 'compute': 200}
        self.save()

    def test_scopes_and_retry_routes(self):
        full = build_manifest(REPO, self.context, 'native-pilot', origin='offline-fixture')
        self.assertEqual(len(full['planned_trials']), 72)
        self.assertEqual(len(self.manifest['planned_trials']), 2)
        self.assertEqual([a['attempt'] for a in full['planned_trials'][0]['attempts']], [1, 2, 3])
        for ids in [[], ['missing'], [self.manifest['planned_trials'][0]['trial_id']] * 2]:
            with self.assertRaises(ValueError): build_manifest(REPO, self.context, 'model-smoke', ids)
        with self.assertRaises(ValueError): build_manifest(REPO, self.context, 'native-pilot', [self.manifest['planned_trials'][0]['trial_id']])

    def test_smoke_reviews_subset_but_pilot_requires_six(self):
        e, _ = self.executor()
        self.assertTrue(self.assess(e)['ready_for_dispatch'])
        full = build_manifest(REPO, self.context, 'native-pilot', origin='offline-fixture')
        result = assess(REPO, self.context, full, e.adapter.inspect(REPO, full), 'offline-fixture', dt.datetime.fromtimestamp(self.clock(), dt.timezone.utc))
        self.assertEqual(next(c['status'] for c in result['checks'] if c['name'] == 'independent_review'), 'missing_input')

    def test_fixture_never_human_review_or_model_authorization(self):
        e, _ = self.executor()
        with self.assertRaises(ValueError): validate_reviews(snapshot(REPO), self.context['reviews'])
        result = self.assess(e, 'model')
        self.assertFalse(result['ready_for_dispatch'])
        self.assertFalse(result['ready_for_model_dispatch'])

    def test_review_template_is_not_accepted(self):
        template = load_json(REPO / 'configs/review-records.stage5.template.json')
        with self.assertRaises(ValueError): validate_reviews(snapshot(REPO), template['records'])

    def test_missing_configuration_and_scope_or_attempt_drift(self):
        changed = copy.deepcopy(self.manifest)
        changed['planned_trials'][0]['attempts'] = []
        with self.assertRaises(ValueError): validate_manifest(REPO, self.context, changed)
        self.context['profile']['configurations'].pop()
        with self.assertRaises(ValueError): validate_manifest(REPO, self.context, self.manifest)

    def test_config_changed_after_preview_zero_calls(self):
        e, p = self.executor()
        self.assertTrue(self.assess(e)['ready_for_dispatch'])
        self.context['profile']['configurations'][0]['max_turns'] += 1
        self.save()
        self.assertEqual(e.run_one(e.ids()[0]), 'gate-blocked')
        self.assertEqual(p.call_count(), 0)
        self.assertFalse((self.root / 'state/ledger.sqlite3').exists())

    def test_snapshot_drift_in_frozen_manifest_zero_calls(self):
        self.manifest['snapshot_id'] = 'old'
        e, p = self.executor()
        self.assertEqual(e.run_one(e.ids()[0]), 'gate-blocked')
        self.assertEqual(p.call_count(), 0)

    def test_effective_settings_are_observed_independently(self):
        e, p = self.executor()
        settings = load_json(self.root / 'effective-settings.json')
        settings['profile']['configurations'][0]['max_tokens'] += 1
        write_json(self.root / 'effective-settings.json', settings)
        self.assertEqual(e.run_one(e.ids()[0]), 'gate-blocked')
        self.assertEqual(p.call_count(), 0)

    def test_attestation_expired_after_preview_zero_calls(self):
        e, p = self.executor()
        self.assertTrue(self.assess(e)['ready_for_dispatch'])
        self.clock.advance(301)
        self.assertEqual(e.run_one(e.ids()[0]), 'gate-blocked')
        self.assertEqual(p.call_count(), 0)

    def test_each_missing_gate_input_zero_calls(self):
        e, p = self.executor()
        for name, value in [('runtime_evidence', None), ('reviews', []), ('budget_evidence', None)]:
            altered = copy.deepcopy(self.context)
            altered[name] = value
            write_json(self.root / 'context.json', altered)
            self.assertEqual(e.run_one(e.ids()[0]), 'gate-blocked', name)
        self.assertEqual(p.call_count(), 0)

    def test_budget_unknown_or_wrong_scope_zero_calls(self):
        e, p = self.executor()
        for key, value in [('scope', 'native-pilot'), ('currency', 'USD'), ('cost_uncertain', True)]:
            altered = copy.deepcopy(self.context)
            altered['budget_evidence'][key] = value
            write_json(self.root / 'context.json', altered)
            self.assertEqual(e.run_one(e.ids()[0]), 'gate-blocked')
        self.assertEqual(p.call_count(), 0)

    def test_retry_keeps_attempt_and_request_charges(self):
        e, p = self.executor()
        tid = e.ids()[0]
        p.scenarios = {tid + '@request-1:1': receipt('retryable_infra_error', None, 250, 50)}
        e.run_one(tid); e.run_one(tid)
        self.assertEqual(p.call_count(), 2)
        self.assertEqual(e.store.latest(tid)['number'], 2)
        self.assertEqual(e.store.summary()['known_charges_micro_units'], {'inference': 1250, 'compute': 150})

    def test_agent_failure_not_retried(self):
        e, p = self.executor()
        tid = e.ids()[0]
        p.scenarios = {tid + '@request-1:1': receipt('agent_failure', 0)}
        e.run_one(tid); e.run_one(tid)
        self.assertEqual(p.call_count(), 1)

    def test_resume_after_reserve_no_duplicate(self):
        e, p = self.executor(); tid = e.ids()[0]
        with self.assertRaises(SimulatedCrash): e.run_one(tid, 'after_reserve')
        second, _ = self.executor()
        second.run_one(tid); second.run_one(tid)
        self.assertEqual(p.call_count(), 1)

    def test_submit_without_receipt_never_blind_resends(self):
        e, p = self.executor(); tid = e.ids()[0]
        with self.assertRaises(SimulatedCrash): e.run_one(tid, 'after_submit')
        self.assertEqual(e.run_one(tid), 'active-lease')
        self.clock.advance()
        self.assertEqual(e.run_one(tid), 'uncertain-no-resend')
        e.run_one(tid)
        self.assertEqual(p.call_count(), 0)

    def test_crash_after_provider_receipt_reconciles(self):
        e, p = self.executor(); tid = e.ids()[0]
        with self.assertRaises(SimulatedCrash): e.run_one(tid, 'after_provider')
        self.clock.advance()
        self.assertEqual(e.run_one(tid), 'reconciled')
        self.assertEqual(p.call_count(), 1)
        self.assertEqual(e.store.latest(tid)['phase'], 'completed')

    def test_actual_process_crash_and_new_executor_recovery(self):
        e, p = self.executor(); tid = e.ids()[0]
        code = 'import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from model_executor import *;root=Path(sys.argv[2]);p=FakeProvider(root/"state/fake-provider.sqlite3");e=Executor(Path(sys.argv[3]),lambda:load_json(root/"context.json"),load_json(root/"manifest.json"),FixtureAdapter(p,root/"effective-settings.json"),root/"state",lambda:float(sys.argv[4]));e.run_one(e.ids()[0],"after_provider")'
        result = subprocess.run([sys.executable, '-c', code, str(REPO / 'scripts'), str(self.root), str(REPO), str(self.clock())], capture_output=True, text=True, timeout=20)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('SimulatedCrash', result.stderr)
        self.clock.advance()
        e.run_one(tid)
        self.assertEqual(p.call_count(), 1)
        self.assertEqual(e.store.latest(tid)['phase'], 'completed')

    def test_budget_checked_between_requests_within_trial(self):
        self.two_requests()
        e, p = self.executor(); tid = e.ids()[0]
        p.scenarios = {tid + '@request-1:1': receipt(i=1800)}
        self.assertEqual(e.run_one(tid), 'request-budget-blocked')
        self.assertEqual(p.call_count(), 1)
        self.assertEqual(e.store.latest(tid)['phase'], 'uncertain')
        self.assertEqual(e.store.summary()['known_charges_micro_units']['inference'], 1800)
        e.run_one(e.ids()[1]); self.assertEqual(p.call_count(), 1)

    def test_live_gate_between_requests_blocks_changed_runtime(self):
        self.two_requests()
        e, p = self.executor(); original = e.adapter.send_request
        def dispatch(*args):
            result = original(*args)
            self.context['runtime_evidence']['run_id'] = 'wrong'
            self.save()
            return result
        e.adapter.send_request = dispatch
        self.assertEqual(e.run_one(e.ids()[0]), 'gate-blocked-between-requests')
        self.assertEqual(p.call_count(), 1)

    def test_external_cost_uncertainty_between_requests_is_not_cleared(self):
        self.two_requests()
        e, p = self.executor(); original = e.adapter.send_request
        def dispatch(*args):
            result = original(*args)
            self.context['budget_evidence']['cost_uncertain'] = True
            self.save()
            return result
        e.adapter.send_request = dispatch
        self.assertEqual(e.run_one(e.ids()[0]), 'gate-blocked-between-requests')
        self.assertEqual(p.call_count(), 1)
        self.assertEqual(e.store.latest(e.ids()[0])['actual_i'], 1000)

    def test_two_request_accounting_and_normalized_namespace(self):
        self.two_requests()
        e, p = self.executor(); tid = e.ids()[0]
        e.run_one(tid)
        self.assertEqual(p.call_count(), 2)
        self.assertEqual(e.store.latest(tid)['actual_i'], 2000)
        proof = e.write_export()
        rows = [json.loads(line) for line in (self.root / 'state/export/trials.jsonl').read_text().splitlines()]
        self.assertEqual(rows[0]['data_origin'], 'simulation')
        self.assertIsNone(rows[0]['cost_usd'])
        self.assertEqual(proof['request_count'], 2)
        with self.assertRaises(ValueError): aggregate(rows, e.store.plan['task_manifest'])
        scored = aggregate(rows, e.store.plan['task_manifest'], run_plan=e.store.plan, bootstrap_draws=100)
        self.assertEqual(scored['result_kind'], 'simulation-not-model-evaluation')

    def test_unknown_cost_preserves_reward_and_reservation(self):
        e, p = self.executor(); tid = e.ids()[0]
        p.scenarios = {tid + '@request-1:1': receipt(i=None, c=None)}
        e.run_one(tid)
        self.assertEqual(e.store.latest(tid)['phase'], 'uncertain')
        self.assertEqual(e.store.exposure(), self.context['budget_evidence']['reservation'])
        rows, _ = export(e.store, p, self.root / 'out')
        self.assertEqual(rows[0]['reward'], 1)
        e.run_one(e.ids()[1]); self.assertEqual(p.call_count(), 1)
        request = e.requests.rows(tid, 1)[0]
        p.resolve(request['request_id'], receipt())
        e.run_one(tid)
        self.assertEqual(e.store.latest(tid)['phase'], 'completed')
        self.assertEqual(p.call_count(), 1)

    def test_unknown_provider_or_null_reward_no_model_failure(self):
        e, p = self.executor(); tid = e.ids()[0]
        p.scenarios = {tid + '@request-1:1': receipt(reward=None)}
        self.assertEqual(e.run_one(tid), 'uncertain-invalid-receipt')
        self.assertEqual(e.store.latest(tid)['phase'], 'uncertain')
        e.run_one(e.ids()[1]); self.assertEqual(p.call_count(), 1)

    def test_resume_budget_drift_rejected(self):
        e, p = self.executor(); tid = e.ids()[0]
        with self.assertRaises(SimulatedCrash): e.run_one(tid, 'after_reserve')
        self.context['budget_evidence']['caps']['inference'] += 1
        self.save()
        second, _ = self.executor()
        with self.assertRaises(ValueError): second.run_one(tid)
        self.assertEqual(p.call_count(), 0)

    def test_model_cli_does_not_create_execution_state(self):
        state = self.root / 'never-created'
        result = subprocess.run([sys.executable, str(REPO / 'scripts/model_executor.py'), '--mode', 'model', '--state-dir', str(state), '--output', str(self.root / 'readiness.json')], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(state.exists())
        self.assertFalse(load_json(self.root / 'readiness.json')['ready_for_model_dispatch'])
        self.assertEqual(load_json(self.root / 'readiness.json')['manifest_source'], 'generated-preview-not-executable')

    def test_smoke_rejected_by_pilot_aggregate(self):
        with self.assertRaisesRegex(ValueError, 'smoke'):
            aggregate([], [], run_plan={'kind': 'model-smoke'})
        with self.assertRaisesRegex(ValueError, 'smoke'):
            aggregate([{'execution_scope': 'model-smoke'}], [])

    def test_changed_adapter_capability_blocks_dispatch(self):
        e, p = self.executor()
        settings = load_json(self.root / 'effective-settings.json')
        settings['policy']['max_requests_per_attempt'] = 2
        write_json(self.root / 'effective-settings.json', settings)
        self.assertEqual(e.run_one(e.ids()[0]), 'gate-blocked')
        self.assertEqual(p.call_count(), 0)

    def test_review_hash_drift_blocks_dispatch(self):
        e, p = self.executor()
        self.context['reviews'][0]['payload_sha256'] = 'changed'
        self.save()
        self.assertEqual(e.run_one(e.ids()[0]), 'gate-blocked')
        self.assertEqual(p.call_count(), 0)

    def test_insufficient_cap_blocks_before_first_request(self):
        e, p = self.executor()
        self.context['budget_evidence']['caps']['inference'] = 500
        self.save()
        self.assertEqual(e.run_one(e.ids()[0]), 'gate-blocked')
        self.assertEqual(p.call_count(), 0)

    def test_unknown_request_receipt_never_retried(self):
        e, p = self.executor(); tid = e.ids()[0]
        p.scenarios = {tid + '@request-1:1': receipt('unknown', None, None, None)}
        e.run_one(tid); e.run_one(tid)
        self.assertEqual(p.call_count(), 1)
        self.assertEqual(e.store.latest(tid)['phase'], 'uncertain')

    def test_max_two_retries_on_new_executor_path(self):
        e, p = self.executor(); tid = e.ids()[0]
        p.scenarios = {tid + f'@request-1:{n}': receipt('verifier_error', None, 200, 50) for n in range(1, 4)}
        for _ in range(4): e.run_one(tid)
        self.assertEqual(p.call_count(), 3)
        self.assertEqual(e.store.latest(tid)['number'], 3)
        self.assertEqual(e.store.summary()['known_charges_micro_units']['inference'], 600)

    def test_two_controllers_cannot_dispatch_different_trials_concurrently(self):
        e, p = self.executor()
        outcomes = []
        errors = []
        original = e.adapter.send_request
        def other_controller():
            local = None; provider = None
            try:
                provider = FakeProvider(self.root / 'state/fake-provider.sqlite3')
                local = Executor(REPO, lambda: load_json(self.root / 'context.json'), self.manifest, FixtureAdapter(provider, self.root / 'effective-settings.json'), self.root / 'state', self.clock)
                outcomes.append(local.run_one(local.ids()[1]))
            except Exception as exc: errors.append(type(exc).__name__)
            finally:
                if local: local.close()
                if provider: provider.db.close()
        def first_request(*args):
            thread = threading.Thread(target=other_controller)
            thread.start(); thread.join(timeout=15)
            self.assertFalse(thread.is_alive())
            return original(*args)
        e.adapter.send_request = first_request
        e.run_one(e.ids()[0])
        self.assertEqual(errors, [])
        self.assertEqual(outcomes, ['claim-lost'])
        self.assertEqual(p.call_count(), 1)


if __name__ == '__main__':
    unittest.main()
