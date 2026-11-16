#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
report_path="${1:-reports/stage8-unit-tests.json}"
if [[ -e "$report_path" ]]; then
  echo 'Choose a fresh report path; historical evidence must not be overwritten' >&2
  exit 2
fi
export PATH="$HOME/.local/bin:$PATH"
runtime="${TMPDIR:-/tmp}/vi-terminal-bench-runtime"
export UV_CACHE_DIR="$runtime/cache"
export UV_PYTHON_INSTALL_DIR="$runtime/python"
if [[ ! -x "$runtime/offline-tests/bin/python" ]]; then
  uv python install 3.12.16
  uv venv --python 3.12.16 "$runtime/offline-tests"
fi
"$runtime/offline-tests/bin/python" -c 'import sys; assert sys.version_info[:3] == (3, 12, 16), "Offline test Python version drift"'
# No source/eval of .env; real credentials never enter the native test snapshot.
"$runtime/offline-tests/bin/python" scripts/stage8_run_native.py --output "$report_path"
