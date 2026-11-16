"""Metadata-only CLI: does not read .env values, load credentials or contact an API."""
import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from credential_artifacts import validate_native_inputs


def status(repo):
    repo = Path(repo)
    ignore_check = subprocess.run(['git', 'check-ignore', '--quiet', '--', '.env'], cwd=repo, capture_output=True)
    if ignore_check.returncode not in (0, 1):
        raise ValueError('Git metadata check failed')
    ignored = ignore_check.returncode == 0
    check = subprocess.run(['git', 'ls-files', '--error-unmatch', '--', '.env'], cwd=repo, capture_output=True)
    if check.returncode not in (0, 1):
        raise ValueError('Git metadata check failed')
    tracked = check.returncode == 0
    members = validate_native_inputs(repo)
    return {'schema': 'vi-credential-status/0.1', 'recorded_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'variable': 'OPENAI_API_KEY', 'file_present': (repo / '.env').is_file(),
            'git_ignored': ignored, 'git_tracked': tracked, 'credential_value_read': False,
            'native_source_policy': 'pass', 'native_source_inputs': len(members),
            'auth_status': 'unverified', 'provider_binding': 'not_installed',
            'ready_for_model_dispatch': False, 'model_calls': 0}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists(): raise ValueError('Choose a new report path')
    report = status(Path(__file__).resolve().parents[1])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(report, indent=2) + '\n')
    print('Credential metadata checked; value not read; API calls 0')
