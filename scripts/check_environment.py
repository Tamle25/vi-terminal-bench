"""Collect nonsecret tool versions; no credential or full environment dumps."""
import argparse
import datetime
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path


def probe(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        return {"returncode": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"error": type(exc).__name__, "detail": str(exc)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        harbor = importlib.metadata.version("harbor")
    except importlib.metadata.PackageNotFoundError:
        harbor = None
    report = {"recorded_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "platform": platform.platform(), "python": sys.version, "harbor": harbor, "docker": probe(["docker", "version", "--format", "{{json .}}"]), "git": probe(["git", "--version"])}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Environment report: {args.output}")


if __name__ == "__main__":
    main()
