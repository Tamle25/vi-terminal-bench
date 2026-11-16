#!/usr/bin/env bash
set -euo pipefail
mkdir -p /logs/verifier
set +e
python -I /tests/grader.py > /logs/verifier/checks.json
status=$?
set -e
case "$status" in
  0) printf '1\n' > /logs/verifier/reward.txt ;;
  1) printf '0\n' > /logs/verifier/reward.txt ;;
  *) exit "$status" ;;
esac
