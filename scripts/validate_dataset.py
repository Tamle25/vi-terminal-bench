"""Dependency-free scaffold validation; use --harbor for real schema validation."""
import argparse
import ast
import json
import tomllib
import shlex
from pathlib import Path
from dev_registry import manifest

REPO = Path(__file__).resolve().parents[1]


def validate(use_harbor: bool = False) -> int:
    rows = manifest()
    seen = set()
    for row in rows:
        task_id = row["task_id"]
        if task_id in seen or not task_id or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in task_id):
            raise ValueError(f"Invalid/duplicate task ID: {task_id}")
        seen.add(task_id)
        required = {"family_id", "track", "primary_skill", "task_version", "source", "license_status", "author", "reviewer", "review_status", "split", "languages"}
        if not required.issubset(row):
            raise ValueError(f"Missing metadata: {task_id}")
        task = REPO / "tasks" / task_id
        for name in ["instruction.md", "task.toml", "README.md", "environment/Dockerfile", "environment/generate_fixture.py", "solution/solve.sh", "solution/solve.py", "tests/Dockerfile", "tests/test.sh", "tests/grader.py", "tests/expected.json"]:
            if not (task / name).is_file():
                raise ValueError(f"Missing {task_id}/{name}")
        config = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))
        if config["verifier"]["environment_mode"] != "separate" or config["schema_version"] != "1.4":
            raise ValueError("Expected separate verifier, schema 1.4")
        if config["task"]["version"] != row["task_version"]:
            raise ValueError("Version mismatch")
        for phase in ["environment", "tests"]:
            compose = task / phase / "docker-compose.yaml"
            if compose.read_text(encoding="utf-8") != "services:\n  main:\n    network_mode: none\n":
                raise ValueError("Expected static Docker network isolation")
            for line in (task / phase / "Dockerfile").read_text(encoding="utf-8").splitlines():
                parts = shlex.split(line)
                if parts and parts[0].upper() == "COPY" and not any(p.startswith("--from=") for p in parts):
                    for source in parts[1:-1]:
                        if source.startswith("/") or ".." in Path(source).parts or not (task / phase / source).is_file():
                            raise ValueError(f"Missing/unsafe COPY source: {task_id}/{phase}/{source}")
        if "/app/output" not in config.get("artifacts", []) or "/app/data" not in config["artifacts"] and "/app/incoming" not in config["artifacts"]:
            raise ValueError("Missing output/source artifact declaration")
        fixture = task / "environment/fixture.json"
        if fixture.exists():
            import hashlib
            hashes = json.loads((task / "tests/source-hashes.json").read_text(encoding="utf-8"))
            for name, value in json.loads(fixture.read_text(encoding="utf-8")).items():
                raw = bytes.fromhex(value["hex"]) if "hex" in value else value["utf8"].encode("utf-8")
                if hashes.get(name) != hashlib.sha256(raw).hexdigest():
                    raise ValueError("Fixture/source checksum mismatch")
        if use_harbor:
            from harbor.models.task.config import TaskConfig
            TaskConfig.model_validate(config)
        for language in row["languages"]:
            prompt = REPO / "prompts" / task_id / f"{language}.md"
            if not prompt.is_file() or not prompt.read_text(encoding="utf-8").strip():
                raise ValueError(f"Missing prompt: {prompt}")
        if (task / "instruction.md").read_bytes() != (REPO / "prompts" / task_id / "vi.md").read_bytes():
            raise ValueError("Default instruction must equal Vietnamese prompt")
        for path in task.rglob("*.py"):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for path in task.rglob("*.sh"):
            if b"\r" in path.read_bytes():
                raise ValueError(f"Shell script must use LF: {path}")
        for path in (task / "environment").rglob("*"):
            if path.is_file() and ("solution" in path.parts or "tests" in path.parts or path.name.startswith("expected")):
                raise ValueError("Private grading files in agent context")
        print(f"OK {task_id}: structure, prompts, TOML" + (", Harbor schema" if use_harbor else " (Harbor schema not checked)"))
    if {p.name for p in (REPO / "tasks").iterdir() if p.is_dir()} != seen:
        raise ValueError("Task directories and manifest differ")
    return len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--harbor", action="store_true")
    args = parser.parse_args()
    print(f"Validated {validate(args.harbor)} tasks")
