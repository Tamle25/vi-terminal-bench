"""Prepare immutable stage5 inventory and incomplete review handoff, offline only."""
import datetime as dt
import hashlib
import json
from pathlib import Path
from model_dry_run import dry_run
from pilot_contracts import snapshot
from stage4_handoff_audit import audit


def prepare(repo):
    paths = [repo / 'reports/stage5-input-state.json',
             repo / 'configs/review-records.stage5.template.json']
    if any(path.exists() for path in paths):
        raise ValueError('Stage5 input evidence already exists; do not overwrite')
    baseline = audit(repo)
    snap = snapshot(repo)
    profile = json.loads((repo / 'configs/model-pilot.template.json').read_text(encoding='utf-8'))
    preview = dry_run(profile, repo)
    historical = {str(path.relative_to(repo)).replace('\\', '/'):
                  hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in sorted((repo / 'reports').glob('stage4-*.json*'))}
    historical['jobs/stage4-offline-simulation.tar.gz'] = baseline['simulation']['archive_sha256']
    records = [{'task_id': tid, 'task_version': task['version'],
                'payload_sha256': task['payload_sha256'], 'prompt_hashes': task['prompts'],
                'author': task['author'], 'reviewer': None, 'reviewer_kind': None,
                'reviewed_at': None, 'expert_time_sec': None, 'decision': None, 'notes': None}
               for tid, task in snap['tasks'].items()]
    template = {'kind': 'incomplete-review-template-not-evidence',
                'snapshot_id': snap['id'], 'records': records,
                'instructions': 'An actual independent human completes each record. Supply a JSON array of completed records to review_records.py; do not import this template.'}
    report = {'schema': 'vi-stage5-input/0.1',
              'recorded_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'scope': 'offline-engineering', 'snapshot': snap,
              'historical_archives': baseline['archive_inventory'],
              'stage4_evidence_sha256': historical,
              'missing_profile_fields': preview['missing_inputs'],
              'review_accepted': 0, 'review_total': 6,
              'states': [
                  {'name': 'historical_evidence', 'status': 'pass', 'source': 'stage4_handoff_audit.audit'},
                  {'name': 'reviewer_and_records', 'status': 'missing_input', 'source': 'manifest.jsonl', 'next_action': 'Owner assigns an independent Vietnamese engineer; obtain actual hash-bound records'},
                  {'name': 'agent_model_and_budget', 'status': 'missing_input', 'source': 'configs/model-pilot.template.json', 'next_action': 'Owner supplies two concrete profiles and smoke/pilot caps'},
                  {'name': 'runtime_choice', 'status': 'missing_input', 'source': 'configs/runtime-profiles.json', 'next_action': 'Select profile then capture fresh run-scoped evidence'},
                  {'name': 'real_adapter_and_isolation', 'status': 'unverified', 'source': 'reports/stage4-readiness.md', 'next_action': 'Verify actual selected adapter, API architecture, usage/cost and cleanup'},
                  {'name': 'part_A', 'status': 'missing_input', 'source': 'docs/eval-input-checklist.md', 'next_action': 'Eval snapshot/config still unavailable'},
                  {'name': 'publication', 'status': 'not_applicable', 'source': 'Plan/plan-giai-doan-5.md', 'next_action': 'Separate owner decision'}],
              'model_calls': 0, 'secrets_read': False}
    for path, value in zip(paths, [report, template]):
        with path.open('x', encoding='utf-8') as handle:
            handle.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    print('Stage5 historical hashes checked; review template incomplete; no model calls')


if __name__ == '__main__':
    prepare(Path(__file__).resolve().parents[1])
