"""Inspect only this project's live Docker containers; never dump environment vars."""
import argparse
import datetime
import json
import subprocess
from pathlib import Path


def inspect_containers(projects):
    ids = subprocess.check_output(["docker", "ps", "-q"], text=True).split()
    snapshots = []
    for identifier in ids:
        data = json.loads(subprocess.check_output(["docker", "inspect", identifier], text=True))[0]
        name = data["Name"].lstrip("/")
        project = data["Config"].get("Labels", {}).get("com.docker.compose.project")
        if project not in projects:
            continue
        snapshots.append({"container": name, "image_id": data["Image"], "network_mode": data["HostConfig"]["NetworkMode"], "memory_bytes": data["HostConfig"]["Memory"], "nano_cpus": data["HostConfig"]["NanoCpus"], "read_only_mount_destinations": [mount["Destination"] for mount in data["Mounts"] if not mount["RW"]]})
    return snapshots


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project", action="append", required=True, help="Exact Docker Compose project label; repeatable")
    args = parser.parse_args()
    snapshots = inspect_containers(set(args.project))
    report = {"kind": "live-container-snapshot-not-exhaustive-security-audit", "recorded_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "snapshots": snapshots, "all_observed_network_none": bool(snapshots) and all(row["network_mode"] == "none" for row in snapshots)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Observed {len(snapshots)} project containers; network_none={report['all_observed_network_none']}")
    raise SystemExit(0 if report["all_observed_network_none"] else 1)
