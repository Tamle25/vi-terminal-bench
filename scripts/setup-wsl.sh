#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
export PATH="$HOME/.local/bin:$PATH"
# Native Linux temporary storage avoids executable/symlink issues on Windows drives.
runtime="${TMPDIR:-/tmp}/vi-terminal-bench-runtime"
export UV_CACHE_DIR="$runtime/cache"
export UV_PYTHON_INSTALL_DIR="$runtime/python"
export UV_PROJECT_ENVIRONMENT="$runtime/venv"
uv sync --locked --python 3.12.16 --group harness
uv run --no-sync harbor --version
