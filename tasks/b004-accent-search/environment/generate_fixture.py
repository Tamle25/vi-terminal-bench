"""Generate explicitly authored fixture bytes; contains no grading answers."""
import argparse
import json
from pathlib import Path


def generate(root):
    fixtures = json.loads((Path(__file__).parent / "fixture.json").read_text(encoding="utf-8"))
    for relative, item in fixtures.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(bytes.fromhex(item["hex"]) if "hex" in item else item["utf8"].encode("utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/app"))
    generate(parser.parse_args().root)
