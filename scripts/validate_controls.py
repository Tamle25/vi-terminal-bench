"""Meaningful positive/negative verifier controls. Run in Linux for filenames.

This is verifier development, NOT a model benchmark and NOT a Harbor isolation test.
"""
import argparse
import datetime
import json
import platform
import runpy
import sys
import tempfile
import unicodedata
from pathlib import Path

from dev_registry import manifest, hooks

REPO = Path(__file__).resolve().parents[1]


def validate(output: Path, selected=None):
    if platform.system() != "Linux":
        raise RuntimeError("Run controls inside Linux: case-distinct filenames and symlinks are required")
    results = []
    tasks = [row for row in manifest() if row["track"] == "B"]
    if selected:
        unknown = set(selected) - {row["task_id"] for row in tasks}
        if unknown:
            raise ValueError(f"Unknown tasks: {unknown}")
        tasks = [row for row in tasks if row["task_id"] in selected]
    for row in tasks:
        task = REPO / "tasks" / row["task_id"]
        registered = hooks(task.name)
        generator, solve = registered["generate"], registered["solve"]
        grade, rejection = registered["grade"], registered["rejection"]
        with tempfile.TemporaryDirectory(prefix="vi-controls-probe-") as directory:
            cases = ["oracle-1", "oracle-2", "oracle-3", "alternative", "no-op", *registered["controls"](Path(directory))]
        for case in cases:
            should_pass = case.startswith("oracle-") or case == "alternative"
            with tempfile.TemporaryDirectory(prefix="vi-controls-") as directory:
                root = Path(directory)
                generator(root)
                if case == "alternative":
                    registered["alternative"](root)
                elif case != "no-op":
                    solve(root)
                    if not case.startswith("oracle-"):
                        registered["controls"](root)[case]()
                reason = None
                try:
                    grade(root)
                    passed = True
                except rejection as exc:
                    passed, reason = False, str(exc)
                matched = passed == should_pass
                results.append({"task_id": task.name, "control": case, "expected_pass": should_pass, "actual_pass": passed, "matched": matched, "reason": reason})
                print(f"{'OK' if matched else 'FAILED'} {task.name} {case}")
    metadata = {"kind": "verifier-controls-not-model-evaluation", "python": sys.version, "unicode_version": unicodedata.unidata_version, "platform": platform.platform(), "recorded_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "controls": results}
    metadata["all_matched"] = all(row["matched"] for row in results)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata["all_matched"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=REPO / "reports/controls.json")
    parser.add_argument("--task", action="append")
    args = parser.parse_args()
    raise SystemExit(0 if validate(args.output, args.task) else 1)
