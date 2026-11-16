"""Build one-language datasets without changing task payloads. No overwrites."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def payload_hash(task: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(task.rglob("*"), key=lambda item: item.relative_to(task).as_posix()):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc" or path.relative_to(task).as_posix() == "instruction.md":
            continue
        digest.update(path.relative_to(task).as_posix().encode("utf-8") + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def materialize(language: str, destination: Path) -> list[dict]:
    rows = [json.loads(line) for line in (REPO / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if destination.exists():
        raise ValueError(f"Refusing to overwrite existing dataset: {destination}")
    # Check all inputs before creating a partial dataset.
    for row in rows:
        task_id = row["task_id"]
        if Path(task_id).name != task_id or "/" in task_id or "\\" in task_id or task_id in {".", ".."}:
            raise ValueError("Unsafe task ID")
        if language not in row["languages"] or not (REPO / "prompts" / task_id / f"{language}.md").is_file():
            raise ValueError(f"Missing {language} prompt for {task_id}")
    destination.mkdir(parents=True)
    manifest = []
    for row in rows:
        task_id = row["task_id"]
        source = REPO / "tasks" / task_id
        target = destination / task_id
        shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        prompt = (REPO / "prompts" / task_id / f"{language}.md").read_bytes()
        (target / "instruction.md").write_bytes(prompt)
        original_hash = payload_hash(source)
        if payload_hash(target) != original_hash:
            raise RuntimeError(f"Payload drift: {task_id}")
        manifest.append({**row, "language": language, "instruction_sha256": hashlib.sha256(prompt).hexdigest(), "payload_sha256": original_hash})
    (destination / "variant-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=["en", "vi", "vi_ascii", "vi_mixed"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for entry in materialize(args.language, args.output):
        print(f"{entry['task_id']}: payload {entry['payload_sha256']}")
