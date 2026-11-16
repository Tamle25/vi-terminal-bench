"""Small scoped executor integration: 2 fixture trials, no repeated 72-trial run."""
import hashlib
import json
import platform
import sys
import tarfile
import tempfile
from pathlib import Path
from aggregate_results import aggregate
from executor_fixtures import fixture, write_json
from model_executor import Executor, FixtureAdapter, load_json, source_hashes
from pilot_runner import Store, FakeProvider
from runtime_process import run_bounded


def validate(repo):
    output = repo / 'reports/stage5-offline-summary.json'
    archive = repo / 'jobs/stage5-scoped-executor.tar.gz'
    if output.exists() or archive.exists():
        raise ValueError('Do not overwrite offline validation evidence')
    with tempfile.TemporaryDirectory(prefix='stage5-input-', dir=repo / 'build') as inputs, tempfile.TemporaryDirectory(prefix='vi-stage5-state-') as state:
        inputs, state = Path(inputs), Path(state)
        context, manifest = fixture(repo, inputs, requests=2)
        seam = Executor(repo, lambda: context, manifest, FixtureAdapter(None, inputs / 'effective-settings.json'), state)
        tid = seam.ids()[0]
        scenarios = {tid + '@request-1:1': {'status': 'retryable_infra_error', 'reward': None, 'inference_micros': 250, 'compute_micros': 50}}
        write_json(inputs / 'scenarios.json', scenarios)
        command = [sys.executable, str(repo / 'scripts/model_executor.py'), '--mode', 'offline-fixture',
                   '--context', str(inputs / 'context.json'), '--manifest', str(inputs / 'manifest.json'),
                   '--settings', str(inputs / 'effective-settings.json'), '--scenarios', str(inputs / 'scenarios.json'),
                   '--state-dir', str(state)]
        first = run_bounded([*command, '--max-attempts', '1', '--output', str(state / 'process-first.json')], timeout=90)
        if first['returncode'] != 2 or first['timed_out']:
            raise ValueError('Expected deliberate partial process: ' + first['stderr'])
        partial = load_json(state / 'process-first.json')
        if partial['summary']['fake_dispatch_calls'] != 1 or partial['summary']['unfinished_trials'] != 2:
            raise ValueError('Expected one retryable attempt before stopping')
        second = run_bounded([*command, '--output', str(state / 'process-resumed.json')], timeout=90)
        if second['returncode'] != 0 or second['timed_out']:
            raise ValueError('Resumed scoped executor failed: ' + second['stderr'])
        third = run_bounded([*command, '--output', str(state / 'process-completed-resume.json')], timeout=90)
        if third['returncode'] != 0 or third['timed_out']:
            raise ValueError('Completed scoped executor resume failed: ' + third['stderr'])
        proof = load_json(state / 'export/executor-provenance.json')
        final = proof['summary']
        expected = {'inference': 4250, 'compute': 450}
        if final['valid_final_trials'] != 2 or final['attempts'] != 3 or final['fake_dispatch_calls'] != 5 or proof['request_count'] != 5 or final['known_charges_micro_units'] != expected or proof['known_request_charges_micro_units'] != expected or final['unfinished_trials'] or final['unknown_cost_attempts']:
            raise ValueError('Scoped request/attempt accounting mismatch')
        if load_json(state / 'process-resumed.json')['summary']['fake_dispatch_calls'] != final['fake_dispatch_calls']:
            raise ValueError('Completed resume dispatched again')
        # All child processes closed SQLite before archival.
        with tarfile.open(archive, 'w:gz') as handle:
            for path in sorted(state.iterdir()):
                handle.add(path, arcname='state/' + path.name)
            handle.add(inputs, arcname='inputs')
            for name in source_hashes():
                handle.add(repo / 'scripts' / name, arcname='source/' + name)
        with tempfile.TemporaryDirectory(prefix='vi-stage5-restore-') as restored:
            with tarfile.open(archive, 'r:gz') as handle:
                handle.extractall(restored, filter='data')
            restored = Path(restored)
            plan = seam.ledger_plan(context)
            store = Store(restored / 'state/ledger.sqlite3', plan)
            provider = FakeProvider(restored / 'state/fake-provider.sqlite3', scenarios)
            try:
                if store.summary()['valid_final_trials'] != 2 or provider.call_count() != 5:
                    raise ValueError('Restored ledger/provider mismatch')
                if store.db.execute('SELECT count(*) FROM execution_requests').fetchone()[0] != 5:
                    raise ValueError('Restored per-request state mismatch')
            finally:
                store.db.close(); provider.db.close()
        rows = [json.loads(line) for line in (state / 'export/trials.jsonl').read_text(encoding='utf-8').splitlines()]
        for row in rows:
            row['raw_reference'] = 'jobs/' + archive.name + '::state/export/raw/' + Path(row['raw_reference']).name
        result = aggregate(rows, plan['task_manifest'], run_plan=plan, bootstrap_draws=100)
        if result['result_kind'] != 'simulation-not-model-evaluation' or len(result['final_trials']) != 2 or any(group['provisional'] for group in result['groups']):
            raise ValueError('Scoped simulation normalization mismatch')
        (repo / 'reports/stage5-fixture-trials.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
        report = {'schema': 'vi-stage5-offline/0.1', 'kind': 'offline-executor-not-model-evaluation',
                  'platform': platform.platform(), 'python': platform.python_version(),
                  'target_scope': 'model-smoke', 'origin': 'offline-fixture',
                  'logical_trials': 2, 'attempts': 3, 'requests': 5, 'fake_dispatch_calls': 5,
                  'partial_process_calls': 1, 'completed_resume_no_redispatch': True,
                  'known_attempt_and_request_charges_micro_units': expected,
                  'currency': 'SIM_USD', 'price_source': 'synthetic-not-provider-pricing',
                  'real_cost_usd': None, 'model_calls': 0, 'secrets_read': False,
                  'restored_databases_verified': True, 'archive': 'jobs/' + archive.name,
                  'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                  'source_files_sha256': source_hashes(), 'snapshot_id': manifest['snapshot_id'],
                  'limitations': 'Fixture reviews, runtime, usage and receipts; not a real smoke. Restore checks durable state, not dispatch from relocated fixture prompt paths.'}
        with output.open('x', encoding='utf-8') as handle:
            handle.write(json.dumps(report, indent=2) + '\n')
        print('Scoped executor validated: 2 fixture trials, 3 attempts, 5 requests; model calls=0')


if __name__ == '__main__':
    validate(Path(__file__).resolve().parents[1])
