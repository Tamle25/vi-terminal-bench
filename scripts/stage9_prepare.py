"""Freeze stage9 public inputs and verify inherited evidence; never read .env."""
import json
from pathlib import Path

from credential_artifacts import validate_native_inputs
from credential_status import status
from pilot_contracts import snapshot
from provider_connectivity_v1 import SOURCES, digest, validate, write_new


def prepare(repo):
    read = lambda name: json.loads((repo / name).read_text(encoding='utf-8'))
    checked = {}
    groups = [read('reports/stage8-unit-tests.json')['input_sha256'],
              read('reports/stage8-summary.json')['source_sha256'],
              read('reports/stage8-input-state.json')['stage7_evidence_sha256'],
              read('reports/stage7-input-state.json')['historical_artifact_sha256'],
              read('reports/stage7-input-state.json')['existing_source_sha256']]
    for group in groups:
        for name, expected in group.items():
            if digest(repo / name) != expected:
                raise ValueError('Historical public input/evidence changed: ' + name)
            checked[name] = expected
    current = snapshot(repo)
    if current['id'] != read('reports/stage8-summary.json')['snapshot_id']:
        raise ValueError('Task snapshot changed')
    validate_native_inputs(repo)
    credential = status(repo)
    if not credential['git_ignored'] or credential['git_tracked']:
        raise ValueError('Credential Git policy failed')
    # Legacy metadata CLI reports historical binding status; do not reuse it as
    # the readiness authority for the newly implemented connectivity binding.
    spec = read('configs/stage9-connectivity.json')
    validate(spec)
    manifest = {'schema': 'vi-connectivity-frozen-inputs/1', 'client_date': '2026-11-13',
                'scope': 'provider-connectivity', 'spec_sha256': digest(repo / 'configs/stage9-connectivity.json'),
                'source_sha256': {name: digest(repo / name) for name in SOURCES},
                'snapshot_id': current['id'], 'inherited_verified_files': len(checked),
                'historical_sha256': checked,
                'inherited_stage8_reports_sha256': {name: digest(repo / name) for name in [
                    'reports/stage8-summary.json', 'reports/stage8-input-state.json', 'reports/stage8-unit-tests.json']},
                'credential_metadata': {k: credential[k] for k in [
                    'file_present', 'git_ignored', 'git_tracked', 'credential_value_read', 'native_source_policy']},
                'benchmark_review_accepted': 0, 'benchmark_review_total': 6,
                'model_smoke_ready': False, 'native_pilot_ready': False,
                'authorization': spec['authorization'], 'cap_usd': spec['cap_usd'],
                'provider_project_id': None, 'account_reference': spec['account_reference']}
    write_new(repo / 'reports/stage9-frozen-inputs.json', manifest)
    print('Public inputs frozen; historical files verified:', len(checked), '; credential value not read')


if __name__ == '__main__':
    prepare(Path(__file__).resolve().parents[1])
