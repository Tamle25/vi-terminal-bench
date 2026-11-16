#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
runtime="${TMPDIR:-/tmp}/vi-terminal-bench-runtime"
if [[ "${1:-}" == "run" || ( "${1:-}" == "job" && "${2:-}" == "start" ) ]]; then
  arguments=("$@")
  jobs_dir=""
  for ((index=0; index<${#arguments[@]}; index++)); do
    case "${arguments[index]}" in
      -o|--jobs-dir) jobs_dir="${arguments[index+1]:-}" ;;
      --jobs-dir=*) jobs_dir="${arguments[index]#*=}" ;;
      -o?*) jobs_dir="${arguments[index]#-o}" ;;
    esac
  done
  if [[ -n "$jobs_dir" ]]; then
    case "$(realpath -m -- "$jobs_dir")" in
      /mnt/*) printf '%s\n' 'Store jobs on native Linux (for example /tmp/vi-terminal-bench-runtime/jobs), not a Windows-mounted drive: Unicode/case-distinct artifacts may be lost.' >&2; exit 2 ;;
    esac
  else
    set -- "$@" --jobs-dir "$runtime/jobs"
  fi
fi
exec "$runtime/venv/bin/harbor" "$@"
