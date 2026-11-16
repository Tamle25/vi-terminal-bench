#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
bench_home="${VI_BENCH_HOME:-$HOME/vi-terminal-bench-stage11}"
export PATH="$HOME/.local/bin:$PATH"
if [[ ! -x "$bench_home/venv/bin/python" ]]; then
  uv python install 3.12.16
  uv venv --python 3.12.16 "$bench_home/venv"
fi
exec "$bench_home/venv/bin/python" scripts/dev_benchmark.py "$@"
