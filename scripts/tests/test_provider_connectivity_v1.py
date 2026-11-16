import copy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import provider_connectivity_v1 as p


class ConnectivityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        root = Path(__file__).resolve().parents[2]
        for name in p.SOURCES:
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((root / name).read_bytes())
        self.spec = json.loads((self.repo / p.SOURCES[0]).read_text(encoding='utf-8'))
        self.manifest = {'source_sha256': {n: p.digest(self.repo / n) for n in p.SOURCES},
                         'spec_sha256': p.digest(self.repo / p.SOURCES[0])}
        (self.repo / '.env').write_text('OPENAI_API_KEY=sk-test-fixture-never-real\n', encoding='utf-8')
        self.db = self.repo / 'state/ledger.sqlite3'
        self.calls = 0

    def body(self):
        return {'id': 'resp_fixture', 'model': p.MODEL, 'status': 'completed', 'service_tier': 'default',
                'usage': {'input_tokens': 100, 'output_tokens': 10,
                          'input_tokens_details': {'cached_tokens': 20}}, 'output': []}

    def transport(self, key, spec):
        self.calls += 1
        self.assertEqual(key, 'sk-test-fixture-never-real')
        return {'http_status': 200, 'provider_request_id': 'req_fixture', 'response': self.body()}

    def run_once(self, transport=None):
        return p.execute(self.repo, self.spec, self.manifest, self.db, transport or self.transport)

    def test_success_has_decimal_cost_and_no_benchmark_score(self):
        result = self.run_once()
        self.assertTrue(result['connectivity_passed'])
        self.assertEqual(result['token_price_estimate_usd'], '0.0001065')
        self.assertIsNone(result['authoritative_invoice_usd'])
        self.assertEqual(result['benchmark_trials'], 0)
        self.assertEqual(result['exposure_held_usd'], '0.01')

    def test_reexecution_never_resends(self):
        self.run_once()
        with self.assertRaises(sqlite3.IntegrityError): self.run_once()
        self.assertEqual(self.calls, 1)

    def test_preexisting_submitted_claim_never_resends(self):
        self.db.parent.mkdir(parents=True)
        with closing(sqlite3.connect(self.db)) as db:
            p.claim(db, self.spec, self.manifest)
            db.execute('UPDATE runs SET state="submitted"')
            db.commit()
        with self.assertRaises(sqlite3.IntegrityError): self.run_once()
        self.assertEqual(self.calls, 0)

    def test_timeout_retains_exposure_and_redacts_error(self):
        def timeout(key, spec):
            self.calls += 1
            raise TimeoutError('Bearer ' + key)
        result = self.run_once(timeout)
        self.assertIsNone(result['token_price_estimate_usd'])
        self.assertEqual(result['accounting_state'], 'unknown_cost_reservation_held')
        self.assertNotIn('sk-test', json.dumps(result))
        with self.assertRaises(sqlite3.IntegrityError): self.run_once()
        self.assertEqual(self.calls, 1)

    def test_http_error_is_not_free_or_success(self):
        result = self.run_once(lambda k, s: {'http_status': 429, 'response': {'error': {'code': 'insufficient_quota'}}})
        self.assertFalse(result['connectivity_passed'])
        self.assertIsNone(result['token_price_estimate_usd'])
        self.assertEqual(result['exposure_held_usd'], '0.01')

    def test_response_exact_key_is_redacted(self):
        result = self.run_once(lambda k, s: {'http_status': 400, 'response': {'error': {'message': k}}})
        self.assertNotIn('sk-test', json.dumps(result))
        self.assertEqual(result['response']['error']['message'], '[REDACTED]')

    def test_drift_prevents_credential_loading_and_network(self):
        (self.repo / p.SOURCES[1]).write_text('changed', encoding='utf-8')
        with patch.object(p, 'credential_scope', side_effect=AssertionError('must not read key')):
            with self.assertRaisesRegex(ValueError, 'SOURCE_DRIFT'): self.run_once()
        self.assertEqual(self.calls, 0)
        self.assertFalse(self.db.exists())

    def test_inmemory_spec_drift_denied(self):
        self.spec['account_reference'] = 'different'
        with self.assertRaisesRegex(ValueError, 'SPEC_DRIFT'): self.run_once()
        self.assertFalse(self.db.exists())

    def test_budget_cap_and_reservation_denied(self):
        for cap, reserve in [('2.01', '0.01'), ('0.001', '0.01'), ('2', '0.0001'), ('NaN', '0.01')]:
            spec = copy.deepcopy(self.spec)
            spec.update(cap_usd=cap, reservation_usd=reserve)
            with self.assertRaises(ValueError): p.validate(spec)

    def test_other_models_tools_retries_or_endpoints_cannot_be_selected(self):
        for field, value in [('model', 'other'), ('tools', [{'type': 'web_search'}]), ('max_output_tokens', 129)]:
            spec = copy.deepcopy(self.spec); spec['request'][field] = value
            with self.assertRaises(ValueError): p.validate(spec)
        spec = copy.deepcopy(self.spec); spec['max_requests'] = 2
        with self.assertRaises(ValueError): p.validate(spec)

    def test_missing_or_unsupported_usage_does_not_coerce_to_zero(self):
        for body in [{}, {'usage': {}}, self.body()]:
            if body.get('model'): body['usage']['input_tokens_details'] = {}
            self.assertIsNone(p.cost(self.spec, body))
        for field, value in [('input_tokens', True), ('output_tokens', -1), ('input_tokens', 10000)]:
            body = self.body(); body['usage'][field] = value
            self.assertIsNone(p.cost(self.spec, body))
        body = self.body(); body['service_tier'] = 'priority'
        self.assertIsNone(p.cost(self.spec, body))

    def test_gate_live_before_secret_sink(self):
        import scoped_credentials as credentials
        original = credentials._dotenv
        def drift(path):
            value = original(path)
            (self.repo / p.SOURCES[1]).write_text('changed', encoding='utf-8')
            return value
        with patch.object(credentials, '_dotenv', side_effect=drift): result = self.run_once()
        self.assertEqual(result['request_attempts'], 0)
        self.assertIn('credential_or_gate_error', result)
        self.assertEqual(self.calls, 0)

    def test_transport_commits_submission_before_dispatch(self):
        def observe(key, spec):
            with closing(sqlite3.connect(self.db)) as db:
                row = db.execute('SELECT state,reserve FROM runs').fetchone()
            self.assertEqual(row, ('submitted', '0.01'))
            return self.transport(key, spec)
        self.run_once(observe)

    def test_http_transport_disables_redirect_and_retry(self):
        with patch.object(p.http.client, 'HTTPSConnection') as factory:
            response = factory.return_value.getresponse.return_value
            response.status = 307
            response.read.return_value = b'{"error":{"code":"redirect"}}'
            response.getheader.return_value = 'req_fixture'
            observed = p.request_once('fixture', self.spec)
            self.assertEqual(observed['http_status'], 307)
            self.assertEqual(factory.call_args.args, ('api.openai.com',))
            self.assertEqual(factory.return_value.request.call_count, 1)
            self.assertEqual(factory.return_value.request.call_args.args[:2], ('POST', '/v1/responses'))
            factory.return_value.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
