"""Small billing/recovery fixtures; no real account, reviewer or model choices."""
from executor_fixtures import fixture, write_json
from execution_contracts import build_manifest
from model_dry_run import dry_run


def billing_fixture(repo, root, run_id, scope='model-smoke', requests=1, now=None):
    context, _ = fixture(repo, root, scope=scope, requests=requests, now=now)
    context['profile']['run_id'] = run_id
    context['runtime_evidence']['run_id'] = run_id
    preview = dry_run(context['profile'], repo)
    selected = [preview['planned_trials'][0]['trial_id'], next(row['trial_id'] for row in preview['planned_trials'] if row['configuration'] == 'candidate-b' and row['language'] == 'vi')]
    manifest = build_manifest(repo, context, scope, selected if scope == 'model-smoke' else None, 'offline-fixture')
    context['budget_evidence'].update(run_id=run_id, scope=scope, manifest_sha256=manifest['manifest_sha256'])
    write_json(root / 'context.json', context)
    write_json(root / 'manifest.json', manifest)
    write_json(root / 'effective-settings.json', {key: context[key] for key in ['origin', 'profile', 'runtime_catalog', 'policy']})
    return context, manifest
