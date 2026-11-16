"""Trusted data-only grading helpers; copy into each dedicated verifier image."""
import argparse
import hashlib
import json
import stat
from pathlib import Path

MAX_BYTES = 1024 * 1024


class Rejected(ValueError):
    pass


def safe_path(root, relative):
    path = root
    for part in Path(relative).parts:
        if part in {"..", "/"}:
            raise Rejected("Unsafe artifact path")
        path = path / part
        if path.is_symlink():
            raise Rejected("Symlink artifact")
    return path


def blob(root, relative):
    path = safe_path(root, relative)
    try:
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise Rejected("Artifact must be a regular file <= 1 MiB")
        return path.read_bytes()
    except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
        raise Rejected(f"Missing/unreadable: {relative}") from exc


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Rejected("Duplicate JSON key")
        result[key] = value
    return result


def json_value(raw):
    if raw.startswith(b"\xef\xbb\xbf"):
        raise Rejected("Unexpected BOM")
    def invalid_constant(value):
        raise Rejected("Nonfinite JSON number")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=object_pairs, parse_constant=invalid_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise Rejected("Invalid JSON/UTF-8") from exc


def same_typed(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(same_typed(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(same_typed(a, b) for a, b in zip(actual, expected))
    return actual == expected


def unchanged(root, trusted):
    hashes = json.loads((trusted / "source-hashes.json").read_text(encoding="utf-8"))
    for relative, digest in hashes.items():
        if hashlib.sha256(blob(root, relative)).hexdigest() != digest:
            raise Rejected(f"Source changed: {relative}")


def entry(grade):
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
