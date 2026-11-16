"""Validate a byte-verified source snapshot on native Linux, not the /mnt mount."""
import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from runtime_process import run_bounded


def inputs(repo):
    paths = [repo / 'manifest.jsonl']
    for directory in ['scripts', 'configs', 'tasks', 'prompts']:
        paths.extend(path for path in (repo / directory).rglob('*')
                     if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc')
    return {path.relative_to(repo).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}


def run(repo, output=None, integration=False):
    if os.name != 'posix' or not sys.platform.startswith('linux'):
        raise ValueError('Run inside Linux/WSL')
    outputs = [repo / 'reports/stage5-offline-summary.json', repo / 'reports/stage5-fixture-trials.jsonl',
               repo / 'jobs/stage5-scoped-executor.tar.gz'] if integration else [output]
    if any(path is None or path.exists() for path in outputs):
        raise ValueError('Choose new output paths; existing evidence must not be overwritten')
    before = inputs(repo)
    with tempfile.TemporaryDirectory(prefix='vi-native-offline-') as temporary:
        native = Path(temporary)
        if str(native.resolve()).startswith('/mnt/'):
            raise ValueError('Native Linux temporary workspace required')
        for relative in before:
            target = native / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(repo / relative, target)
        for directory in ['build', 'reports', 'jobs']:
            (native / directory).mkdir(exist_ok=True)
        if inputs(native) != before:
            raise ValueError('Copied inputs differ from source bytes')
        if integration:
            command = [sys.executable, str(native / 'scripts/stage5_validate_offline.py')]
        else:
            command = [sys.executable, str(native / 'scripts/run_checks.py'), '--output', str(native / 'reports/tests.json')]
        result = run_bounded(command, timeout=300, cwd=str(native))
        if result['timed_out'] or result['returncode'] != 0:
            raise ValueError('Native offline validation failed: ' + result['stderr'] + result['stdout'])
        if inputs(repo) != before:
            raise ValueError('Source changed during validation; do not accept stale results')
        if integration:
            for target in outputs:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as handle:
                    handle.write((native / target.relative_to(repo)).read_bytes())
        else:
            report = json.loads((native / 'reports/tests.json').read_text(encoding='utf-8'))
            report.update(execution_workspace='native-linux-byte-verified-copy',
                          input_sha256=before, python=sys.version)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open('x', encoding='utf-8') as handle:
                handle.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(result['stdout'].strip())
        print('Native source snapshot and original input hashes match; no Docker/model calls')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    parser.add_argument('--integration', action='store_true')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    destination = args.output.resolve() if args.output else None
    run(repo, destination, args.integration)
