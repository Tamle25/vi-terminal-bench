#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
prefix="${1:-stage6}"
if [[ ! "$prefix" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo 'Invalid evidence prefix' >&2
  exit 2
fi
# Keep one WSL session alive across Python bootstrap, tests and integration.
bash scripts/setup-offline-tests.sh "reports/$prefix-unit-tests.json"
runtime="${TMPDIR:-/tmp}/vi-terminal-bench-runtime"
"$runtime/offline-tests/bin/python" scripts/stage6_run_native.py --prefix "$prefix"
