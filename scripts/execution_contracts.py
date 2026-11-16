"""Scoped execution contracts. Fixtures can never attest a real model dispatch."""
import copy
import datetime as dt
from decimal import Decimal
from model_dry_run import dry_run
from pilot_contracts import digest, snapshot, runtime_fingerprint, validate_attestation
from review_records import validate_reviews

SCOPES = {'model-smoke': 'model-smoke', 'native-pilot': 'model-pilot'}
DEFAULT_POLICY = {'tool_access': ['terminal'],
                  'resources': {'source': 'task.toml', 'verifier_network': 'none'},
                  'max_requests_per_attempt': 1,
                  'request_reservation': {'inference': 1000, 'compute': 100}}


def selected_runtime(catalog):
    ids = [item['id'] for item in catalog['profiles']]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate runtime profile')
    for item in catalog['profiles']:
        runtime_fingerprint(item)
        if item['id'] == catalog.get('selected_runtime_profile'):
            return item
    return None


def validate_policy(policy):
    if set(policy) != set(DEFAULT_POLICY):
        raise ValueError('Execution policy schema mismatch')
    if policy['tool_access'] != ['terminal'] or policy['resources'] != DEFAULT_POLICY['resources']:
        raise ValueError('Unverified tool/resource policy')
    if type(policy['max_requests_per_attempt']) is not int or not 1 <= policy['max_requests_per_attempt'] <= 100:
        raise ValueError('Invalid request bound')
    values = policy['request_reservation']
    if set(values) != {'inference', 'compute'} or any(type(v) is not int or v <= 0 for v in values.values()):
        raise ValueError('Request reservations must be positive integer micro-units')


def configuration_hashes(repo, profile, catalog, policy):
    validate_policy(policy)
    preview = dry_run(profile, repo)
    runtime = selected_runtime(catalog)
    result = {}
    for config in profile['configurations']:
        original = next(row for row in preview['planned_trials'] if row['configuration'] == config['id'])
        result[config['id']] = digest({'schema': 'vi-effective-execution/0.1',
            'model_profile': config, 'system_prompt_sha256': original['system_prompt_sha256'],
            'runtime_profile_sha256': runtime_fingerprint(runtime) if runtime else None,
            'concurrency': profile['concurrency'], 'execution_policy': policy})
    return result


def build_manifest(repo, context, scope, trial_ids=None, origin='real'):
    if scope not in SCOPES or origin not in {'real', 'offline-fixture'}:
        raise ValueError('Unknown execution scope/origin')
    profile = context['profile']
    preview = dry_run(profile, repo)
    wanted = {row['trial_id']: row for row in preview['planned_trials']}
    if scope == 'native-pilot':
        if trial_ids is not None and (len(trial_ids) != 72 or set(trial_ids) != set(wanted)):
            raise ValueError('Native pilot must contain exactly all 72 trials')
        ids = list(wanted)
    else:
        ids = list(trial_ids or [])
        if not 1 <= len(ids) <= 2 or len(set(ids)) != len(ids) or not set(ids) <= wanted.keys():
            raise ValueError('Smoke requires 1-2 distinct explicit planned trial IDs')
    hashes = configuration_hashes(repo, profile, context['runtime_catalog'], context['policy'])
    rows = []
    for tid in ids:
        row = copy.deepcopy(wanted[tid])
        row['configuration_sha256'] = hashes[row['configuration']]
        row['attempts'] = [{'attempt': n, 'job_name': f'{tid}-{scope}-a{n}'} for n in range(1, 4)]
        rows.append(row)
    configs = sorted({row['configuration'] for row in rows})
    result = {'schema': 'vi-execution-manifest/0.1',
              'kind': 'simulation' if origin == 'offline-fixture' else SCOPES[scope],
              'origin': origin, 'scope': scope, 'run_id': profile['run_id'],
              'snapshot_id': snapshot(repo)['id'], 'expected_configurations': configs,
              'configuration_fingerprints': {key: hashes[key] for key in configs},
              'policy_sha256': digest(context['policy']), 'planned_trials': rows}
    result['manifest_sha256'] = digest(result)
    return result


def validate_manifest(repo, context, manifest):
    if manifest.get('schema') != 'vi-execution-manifest/0.1':
        raise ValueError('Execution manifest required; preview is insufficient')
    ids = [row['trial_id'] for row in manifest['planned_trials']]
    expected = build_manifest(repo, context, manifest['scope'], ids, manifest['origin'])
    if digest(expected) != digest(manifest):
        raise ValueError('Frozen manifest differs from current snapshot/profile/policy')
    return expected


def validate_fixture_reviews(snap, records):
    accepted = set()
    for row in records:
        if row.get('reviewer_kind') != 'fixture' or row.get('origin') != 'offline-fixture':
            raise ValueError('Only explicit fixture signoffs belong in offline fixture mode')
        tid = row['task_id']
        if tid in accepted or tid not in snap['tasks']:
            raise ValueError('Duplicate/unknown fixture signoff')
        task = snap['tasks'][tid]
        if (row['task_version'], row['payload_sha256'], row['prompt_hashes']) != (task['version'], task['payload_sha256'], task['prompts']):
            raise ValueError('Fixture signoff snapshot mismatch')
        accepted.add(tid)
    return accepted


def assess(repo, context, manifest, observation=None, mode='model', now=None):
    """Same live gate for fixture orchestration and future provider binding; no I/O dispatch."""
    if mode not in {'model', 'offline-fixture'}:
        raise ValueError('Unknown gate mode')
    fixture = mode == 'offline-fixture'
    profile = context['profile']
    current = now or dt.datetime.now(dt.timezone.utc)
    preview = dry_run(profile, repo)
    snap = snapshot(repo)
    checks = []

    def check(name, ok, reason, status='fail'):
        checks.append({'name': name, 'status': 'pass' if ok else status, 'reason': reason})

    check('profile', preview['profile_complete'], 'Required profile fields must be supplied', 'missing_input')
    origin = 'offline-fixture' if fixture else 'real'
    check('origin', context.get('origin') == origin and manifest.get('origin') == origin and manifest.get('kind') == ('simulation' if fixture else SCOPES.get(manifest.get('scope'))), 'Fixture/model boundaries must agree')
    try:
        validate_manifest(repo, context, manifest)
        valid = True
    except (ValueError, KeyError, TypeError):
        valid = False
    check('manifest', valid, 'Frozen scope, snapshot, configuration, policy and attempt routing must match')
    scope = manifest.get('scope')
    required = set(snap['tasks']) if scope == 'native-pilot' else {row['task_id'] for row in manifest.get('planned_trials', [])}
    try:
        accepted = (validate_fixture_reviews(snap, context.get('reviews', [])) if fixture
                    else set(validate_reviews(snap, context.get('reviews', []))))
        reviewed = bool(required) and required <= accepted
    except (ValueError, KeyError, TypeError):
        reviewed = False
    check('independent_review', reviewed, 'Pilot needs 6/6; smoke needs its selected tasks; fixtures are not human reviews', 'missing_input')
    runtime = selected_runtime(context['runtime_catalog'])
    evidence = context.get('runtime_evidence')
    runtime_ok = False
    if runtime:
        status, _ = validate_attestation(runtime, evidence, profile['run_id'], snap['id'], current, profile['concurrency'])
        runtime_ok = status == 'pass' and (fixture or evidence.get('data_origin') != 'offline-fixture')
    check('runtime', runtime_ok, 'Fresh selected runtime attestation for this exact run/snapshot required', 'unverified')
    adapter_ok = bool(observation) and observation.get('origin') == origin and observation.get('run_id') == profile['run_id'] and observation.get('snapshot_id') == snap['id'] and observation.get('configuration_fingerprints') == manifest.get('configuration_fingerprints') and observation.get('policy_sha256') == digest(context['policy']) and bool(observation.get('adapter_id')) and bool(observation.get('adapter_version')) and bool(observation.get('source_sha256'))
    caps = observation.get('capabilities', {}) if observation else {}
    adapter_ok = adapter_ok and caps.get('request_accounting') is True and caps.get('max_requests_per_attempt') == context['policy']['max_requests_per_attempt']
    check('effective_adapter', adapter_ok, 'Adapter-observed settings and provenance must match expected contract', 'unverified')
    budget = context.get('budget_evidence') or {}
    budget_ok = False
    try:
        amounts = [budget[key] for key in ['caps', 'remaining', 'reservation']]
        numeric = all(set(values) == {'inference', 'compute'} and all(type(v) is int and v >= 0 for v in values.values()) for values in amounts)
        cap_i = profile['budget']['smoke_max_usd'] if scope == 'model-smoke' else profile['budget']['max_inference_usd']
        cap_c = profile['budget']['smoke_max_usd'] if scope == 'model-smoke' else profile['budget']['max_compute_usd']
        declared = [int(Decimal(str(value)) * 1000000) for value in [cap_i, cap_c]]
        budget_ok = numeric and all(budget['caps'][key] > 0 and budget['reservation'][key] > 0 and budget['reservation'][key] <= budget['remaining'][key] <= budget['caps'][key] <= declared[index] for index, key in enumerate(['inference', 'compute']))
        if scope == 'model-smoke':
            budget_ok = budget_ok and sum(budget['caps'].values()) <= declared[0]
        budget_ok = budget_ok and budget.get('run_id') == profile['run_id'] and budget.get('scope') == scope and budget.get('manifest_sha256') == manifest.get('manifest_sha256') and budget.get('cost_uncertain') is False and bool(budget.get('price_source')) and budget.get('currency') == ('SIM_USD' if fixture else 'USD') and budget.get('origin') == ('offline-fixture' if fixture else 'provider-estimate-and-ledger') and budget.get('pricing_state') == ('fixture' if fixture else 'verified-current')
        reservation = context['policy']['request_reservation']
        budget_ok = budget_ok and all(reservation[key] * context['policy']['max_requests_per_attempt'] <= budget['reservation'][key] for key in reservation)
    except (KeyError, TypeError, ValueError, ArithmeticError):
        budget_ok = False
    check('budget', budget_ok, 'Scope-bound caps, current source and sufficient known reservation required', 'missing_input')
    # No real provider is registered yet. Evidence JSON cannot enable a binding.
    check('provider_binding', fixture and observation is not None and observation.get('adapter_id') == 'durable-offline-fixture', 'Only a durable offline fixture binding is installed; real provider binding absent', 'unverified')
    ready = all(row['status'] == 'pass' for row in checks)
    return {'schema': 'vi-execution-readiness/0.1', 'recorded_at_utc': current.isoformat(),
            'run_id': profile['run_id'], 'snapshot_id': snap['id'], 'scope': scope,
            'mode': mode, 'checks': checks, 'ready_for_dispatch': ready,
            'ready_for_model_dispatch': False, 'authorization_token': False,
            'model_calls': 0, 'secrets_read': False,
            'note': 'Fixture checks validate orchestration only; no real provider binding installed'}
