#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
agent="${1:?Usage: run_native_validation.sh oracle|nop}"
run_id="${2:-native-six}"
case "$agent" in
  oracle) repeats=3 ;;
  nop) repeats=1 ;;
  *) printf '%s\n' 'Only oracle/nop development validation is supported.' >&2; exit 2 ;;
esac
runtime="${TMPDIR:-/tmp}/vi-terminal-bench-runtime"
python="$runtime/venv/bin/python"
plan="reports/${run_id}-${agent}-run.json"
"$python" scripts/preflight.py --jobs-dir "$runtime/jobs" --output "reports/${run_id}-preflight-${agent}.json"
"$python" scripts/plan_run.py --dataset "$PWD/tasks" --language vi --agent "$agent" --configuration "$agent-validation" --repeats "$repeats" --jobs-root "$runtime/jobs" --run-id "$run_id" --output "$plan"
"$python" scripts/execute_validation_plan.py "$plan"
"$python" scripts/import_harbor_results.py --plan "$plan" --output "reports/${run_id}-${agent}-trials.jsonl"
