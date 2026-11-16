import argparse
import hashlib
import json
import unicodedata
from pathlib import Path


def solve(root: Path) -> None:
    incoming = root / "incoming"
    output = root / "output"
    files = output / "files"
    files.mkdir(parents=True, exist_ok=True)
    records = []
    for number, source in enumerate(sorted(incoming.iterdir(), key=lambda p: p.name), 1):
        target = f"{number:04d}--{unicodedata.normalize('NFC', source.name)}"
        content = source.read_bytes()
        (files / target).write_bytes(content)
        records.append({"source": source.name, "target": target, "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)})
    (output / "index.jsonl").write_bytes("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records).encode("utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/app"))
    solve(parser.parse_args().root)
