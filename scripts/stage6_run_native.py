"""Run stage6 integration on a verified native Linux copy; preserve old outputs."""
import json
import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path
from run_native_offline import inputs
from runtime_process import run_bounded


def run(repo, prefix='stage6'):
    if not sys.platform.startswith('linux'): raise ValueError('Linux/WSL required')
    if not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', prefix): raise ValueError('Invalid evidence prefix')
    outputs = ['reports/' + prefix + '-offline-summary.json', 'jobs/' + prefix + '-shared-billing.tar.gz']
    if any((repo / name).exists() for name in outputs): raise ValueError('Do not overwrite integration evidence')
    before = inputs(repo)
    with tempfile.TemporaryDirectory(prefix='vi-stage6-native-') as temporary:
        native = Path(temporary)
        if str(native.resolve()).startswith('/mnt/'): raise ValueError('Native temporary storage required')
        for relative in before:
            target = native / relative; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(repo / relative, target)
        for folder in ['build', 'reports', 'jobs']: (native / folder).mkdir(exist_ok=True)
        if inputs(native) != before: raise ValueError('Copied input hashes differ')
        result = run_bounded([sys.executable, str(native / 'scripts/stage6_validate_offline.py'), '--prefix', prefix], timeout=180, cwd=str(native))
        if result['timed_out'] or result['returncode'] != 0: raise ValueError('Billing integration failed: ' + result['stderr'])
        if inputs(repo) != before: raise ValueError('Sources changed during integration')
        for relative in outputs:
            target = repo / relative; target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as handle: handle.write((native / relative).read_bytes())
        print(result['stdout'].strip())
        print('Native integration source hashes match workspace')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--prefix', default='stage6')
    run(Path(__file__).resolve().parents[1], parser.parse_args().prefix)
