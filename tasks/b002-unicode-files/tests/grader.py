"""Grade JSON and file bytes without executing submissions."""
import argparse
import hashlib
import json
import stat
import unicodedata
from pathlib import Path

MAX_BYTES = 1024 * 1024


class Rejected(ValueError):
    pass


def safe_path(root: Path, relative: str) -> Path:
    path = root
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink():
            raise Rejected(f"Symlink: {relative}")
    return path


def read_regular(root: Path, relative: str) -> bytes:
    path = safe_path(root, relative)
    try:
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise Rejected(f"Not a bounded regular file: {relative}")
        return path.read_bytes()
    except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
        raise Rejected(f"Missing/unreadable artifact: {relative}") from exc


def names(root: Path, relative: str) -> set[str]:
    path = safe_path(root, relative)
    try:
        if not path.is_dir():
            raise Rejected(f"Missing directory: {relative}")
        return {item.name for item in path.iterdir()}
    except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
        raise Rejected(f"Unreadable directory: {relative}") from exc


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Rejected(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_index(root: Path):
    raw = read_regular(root, "output/index.jsonl")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise Rejected("BOM forbidden")
    try:
        lines = raw.decode("utf-8", errors="strict").split("\n")
        if lines[-1] == "":
            lines.pop()
        if not lines or any(not line.strip() for line in lines):
            raise Rejected("Empty index/blank line")
        def invalid_constant(value):
            raise Rejected(f"Non-finite JSON number: {value}")
        return [json.loads(line, object_pairs_hook=unique_object, parse_constant=invalid_constant) for line in lines]
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise Rejected("Invalid UTF-8/JSON index") from exc


def grade(root: Path) -> None:
    fixtures = json.loads((Path(__file__).parent / "expected.json").read_text(encoding="utf-8"))
    if names(root, "incoming") != {item["source"] for item in fixtures}:
        raise Rejected("Source names changed/missing")
    expected = []
    for number, item in enumerate(sorted(fixtures, key=lambda r: r["source"]), 1):
        content = bytes.fromhex(item["content_hex"]) if "content_hex" in item else item["content_utf8"].encode("utf-8")
        target = f"{number:04d}--{unicodedata.normalize('NFC', item['source'])}"
        if read_regular(root, "incoming/" + item["source"]) != content:
            raise Rejected("Source content changed")
        if read_regular(root, "output/files/" + target) != content:
            raise Rejected("Copied file missing/changed")
        expected.append({"source": item["source"], "target": target, "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content)})
    if names(root, "output/files") != {item["target"] for item in expected}:
        raise Rejected("Extra/missing output file")
    records = read_index(root)
    for row in records:
        if type(row) is not dict or set(row) != {"source", "target", "sha256", "size_bytes"}:
            raise Rejected("Index schema")
        if any(type(row[key]) is not str for key in ["source", "target", "sha256"]) or type(row["size_bytes"]) is not int:
            raise Rejected("Index types")
    if records != expected:
        raise Rejected("Index content/order mismatch")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/app"))
    args = parser.parse_args()
    try:
        grade(args.root)
    except Rejected as exc:
        print(json.dumps({"passed": False, "reason": str(exc)}, ensure_ascii=False))
        return 1
    except Exception as exc:
        print(json.dumps({"verifier_error": type(exc).__name__, "detail": str(exc)}, ensure_ascii=False))
        return 2
    print('{"passed": true}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
