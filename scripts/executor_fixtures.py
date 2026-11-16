"""Explicit offline-only fixtures. Never human review or real model evidence."""
import copy
import datetime as dt
import json
from pathlib import Path
from execution_contracts import DEFAULT_POLICY, build_manifest
from model_dry_run import dry_run
from pilot_contracts import snapshot, runtime_fingerprint


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def fixture(repo, root, *, requests=1, scope='model-smoke', now=None):
    """Root must be under workspace/build; dry_run validates prompt containment."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    current = now or dt.datetime.now(dt.timezone.utc)
    prompt = root / 'fixture-system.md'
    prompt.write_text('Offline orchestration fixture only. No model is called.\n', encoding='utf-8')
    profile = json.loads((repo / 'configs/model-pilot.template.json').read_text(encoding='utf-8'))
    profile['run_id'] = 'stage5-fixture'
    profile['budget'] = {key: 10 for key in profile['budget']}
    for config in profile['configurations']:
        config.update(agent='fixture-agent', agent_version='fixture-v1', model='fixture-model',
                      provider='fixture-provider', endpoint='https://provider.invalid',
                      reasoning_effort='not-applicable',
                      system_prompt_path=prompt.relative_to(repo).as_posix(),
                      max_tokens=100, max_turns=5, timeout_sec=300,
                      architecture='host-agent-offline-sandbox', credential_env_name='FIXTURE_NAME_NEVER_READ')
    catalog = json.loads((repo / 'configs/runtime-profiles.json').read_text(encoding='utf-8'))
    catalog['selected_runtime_profile'] = 'native-wsl-v1'
    runtime = catalog['profiles'][0]
    snap = snapshot(repo)
    attest = {'kind': 'runtime-capture', 'data_origin': 'offline-fixture',
              'run_id': profile['run_id'], 'snapshot_id': snap['id'],
              'runtime_profile_id': runtime['id'], 'runtime_profile_sha256': runtime_fingerprint(runtime),
              'issued_at_utc': current.isoformat(), 'expires_at_utc': (current + dt.timedelta(seconds=300)).isoformat(),
              'preflight': {'ready': True, 'source': 'fixture-not-Docker'},
              'observation': {'user': runtime['user'], 'endpoint_class': runtime['endpoint_class'],
                  'docker_os': 'linux', 'filesystem_capabilities_ok': True,
                  'verifier_network': 'none', 'control_socket_in_sandbox': False,
                  'endpoint': 'unix:///run/docker.sock'}}
    context = {'origin': 'offline-fixture', 'profile': profile, 'runtime_catalog': catalog,
               'policy': copy.deepcopy(DEFAULT_POLICY), 'runtime_evidence': attest}
    context['policy']['max_requests_per_attempt'] = requests
    preview = dry_run(profile, repo)
    ids = [preview['planned_trials'][0]['trial_id'], next(row['trial_id'] for row in preview['planned_trials'] if row['configuration'] == 'candidate-b' and row['language'] == 'vi')]
    manifest = build_manifest(repo, context, scope, ids if scope == 'model-smoke' else None, 'offline-fixture')
    selected = {row['task_id'] for row in manifest['planned_trials']}
    context['reviews'] = [{'origin': 'offline-fixture', 'reviewer_kind': 'fixture',
                           'task_id': tid, 'task_version': snap['tasks'][tid]['version'],
                           'payload_sha256': snap['tasks'][tid]['payload_sha256'],
                           'prompt_hashes': snap['tasks'][tid]['prompts']} for tid in sorted(selected)]
    context['budget_evidence'] = {'origin': 'offline-fixture', 'currency': 'SIM_USD',
        'pricing_state': 'fixture', 'price_source': 'synthetic-not-provider-pricing',
        'run_id': profile['run_id'], 'scope': scope, 'manifest_sha256': manifest['manifest_sha256'],
        'cost_uncertain': False, 'caps': {'inference': 200000, 'compute': 20000},
        'remaining': {'inference': 200000, 'compute': 20000},
        'reservation': {'inference': requests * 2000, 'compute': requests * 200}}
    write_json(root / 'context.json', context)
    write_json(root / 'effective-settings.json', {key: copy.deepcopy(context[key]) for key in ['origin', 'profile', 'runtime_catalog', 'policy']})
    write_json(root / 'manifest.json', manifest)
    return context, manifest
