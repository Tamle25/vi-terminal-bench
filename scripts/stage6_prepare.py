"""Freeze stage6 input evidence without changing historical reports or decisions."""
import datetime as dt
import hashlib
import json
from pathlib import Path
from stage5_handoff_audit import audit


def prepare(repo):
    target = repo / 'reports/stage6-input-state.json'
    if target.exists():
        raise ValueError('Do not overwrite stage6 input evidence')
    prior = audit(repo)
    paths = list((repo / 'reports').glob('stage5-*.json*'))
    paths += [repo / 'jobs/stage5-scoped-executor.tar.gz']
    hashes = {path.relative_to(repo).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}
    report = {'schema': 'vi-stage6-input/0.1', 'run_id': 'stage6-offline-engineering',
              'scope': 'offline-engineering', 'recorded_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'snapshot_id': prior['snapshot_id'], 'stage5_evidence_sha256': hashes,
              'missing_profile_fields': prior['missing_profile_fields'], 'review_accepted': 0, 'review_total': 6,
              'states': [
                  {'name': 'historical_evidence', 'status': 'pass', 'source': 'stage5_handoff_audit.audit'},
                  {'name': 'review', 'status': 'missing_input', 'source': 'configs/review-records.stage5.template.json', 'next_action': 'Owner assigns an independent human; existing template is not acceptance'},
                  {'name': 'model_budget_and_billing_scope', 'status': 'missing_input', 'source': 'configs/model-pilot.template.json', 'next_action': 'Supply two concrete configurations, caps and actual billing scope/account references'},
                  {'name': 'runtime_and_real_binding', 'status': 'unverified', 'source': 'reports/stage5-readiness.md', 'next_action': 'Select and verify runtime, adapter, isolation, usage and provider-specific recovery'},
                  {'name': 'part_A', 'status': 'missing_input', 'source': 'docs/eval-input-checklist.md', 'next_action': 'Eval snapshot/config still unavailable'},
                  {'name': 'publication', 'status': 'not_applicable', 'source': 'Plan/plan-giai-doan-6.md', 'next_action': 'Separate owner decision'}],
              'model_calls': 0, 'secrets_read': False}
    with target.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Stage6 history checked; real review/model/budget/account decisions remain missing')


if __name__ == '__main__':
    prepare(Path(__file__).resolve().parents[1])
