"""Trusted authoring hooks, deliberately outside all agent/verifier images."""
import json
import runpy
import sys
from pathlib import Path

from alternative_solutions import invoice, unicode_files
from control_cases import controls as legacy_controls

REPO = Path(__file__).resolve().parents[1]
REGISTERED = {
    "b001-vn-invoice", "b002-unicode-files", "b003-windows1258",
    "b004-accent-search", "b005-vietnamese-collation", "b006-vietnamese-csv-export",
}


def manifest():
    rows = [json.loads(line) for line in (REPO / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [row["task_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate manifest task")
    for row in rows:
        if row["track"] == "B" and row["task_id"] not in REGISTERED:
            raise ValueError(f"Missing development registration: {row['task_id']}")
    return rows


def hooks(task_id):
    if task_id not in REGISTERED:
        raise ValueError(f"No trusted development hooks: {task_id}")
    task = REPO / "tasks" / task_id
    sys.path.insert(0, str(task / "tests"))
    try:
        grader = runpy.run_path(str(task / "tests/grader.py"))
    finally:
        sys.path.pop(0)
    if task_id in {"b001-vn-invoice", "b002-unicode-files"}:
        alternative = invoice if task_id == "b001-vn-invoice" else unicode_files
        cases = lambda root: legacy_controls(task_id, root)
    else:
        from native_controls import controls
        alternative = runpy.run_path(str(REPO / "scripts/alternatives" / f"{task_id}.py"))["solve"]
        cases = lambda root: controls(task_id, root)
    return {
        "generate": runpy.run_path(str(task / "environment/generate_fixture.py"))["generate"],
        "solve": runpy.run_path(str(task / "solution/solve.py"))["solve"],
        "alternative": alternative, "controls": cases,
        "grade": grader["grade"], "rejection": grader["Rejected"],
    }
