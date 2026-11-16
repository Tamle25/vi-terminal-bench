"""Build fresh agent images and check grading material is not baked in."""
import argparse
import json
import subprocess
from pathlib import Path
from dev_registry import manifest

REPO = Path(__file__).resolve().parents[1]


def check():
    snapshots = []
    code = "from pathlib import Path; import json; assert not Path('/tests').exists(); assert not Path('/solution').exists(); assert not list(Path('/app').rglob('expected*')); print(json.dumps({'tests_absent': True, 'solution_absent': True, 'expected_absent': True}))"
    roster = manifest()
    for row in roster:
        task = REPO / "tasks" / row["task_id"]
        image = subprocess.check_output(["docker", "build", "--quiet", str(task / "environment")], text=True).strip().splitlines()[-1]
        result = subprocess.check_output(["docker", "run", "--rm", "--network", "none", image, "python", "-I", "-c", code], text=True)
        snapshots.append({"task_id": task.name, "image_id": image, **json.loads(result)})
    matched = {row["task_id"] for row in snapshots} == {row["task_id"] for row in roster}
    return {"kind": "fresh-agent-image-check-not-exhaustive-security-audit", "all_matched": matched, "images": snapshots}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = check()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Validated {len(report['images'])} fresh agent images")
    raise SystemExit(0 if report["all_matched"] else 1)
