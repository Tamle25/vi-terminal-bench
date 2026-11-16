import json
import unicodedata


def load_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def save_rows(path, rows):
    path.write_bytes("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode("utf-8"))


def change_rows(path, transform):
    rows = load_rows(path)
    transform(rows)
    save_rows(path, rows)


def controls(task_id, root):
    if task_id == "b001-vn-invoice":
        records = root / "output/hoa_don.jsonl"
        errors = root / "output/errors.jsonl"
        def strip_accents(rows):
            for row in rows:
                row["customer_name"] = "".join(c for c in unicodedata.normalize("NFD", row["customer_name"]) if not unicodedata.combining(c)).replace("Đ", "D").replace("đ", "d")
        def swap_date(rows):
            rows[-1]["invoice_date"] = "2026-03-04"
        def boolean_zero(rows):
            rows[1]["amount_vnd"] = False
        def nfd(rows):
            rows[0]["customer_name"] = unicodedata.normalize("NFD", rows[0]["customer_name"])
        def duplicate_key():
            data = records.read_text(encoding="utf-8")
            records.write_bytes(data.replace('{"invoice_id":', '{"invoice_id":"duplicate", "invoice_id":', 1).encode("utf-8"))
        return {
            "empty-output": lambda: records.write_bytes(b""),
            "first-row-only": lambda: change_rows(records, lambda rows: rows.__delitem__(slice(1, None))),
            "strip-accents": lambda: change_rows(records, strip_accents),
            "month-day-swap": lambda: change_rows(records, swap_date),
            "wrong-amount": lambda: change_rows(records, lambda rows: rows[0].update(amount_vnd=1000)),
            "string-amount": lambda: change_rows(records, lambda rows: rows[0].update(amount_vnd="1000000")),
            "boolean-zero": lambda: change_rows(records, boolean_zero),
            "missing-errors": lambda: errors.unlink(),
            "wrong-error-priority": lambda: change_rows(errors, lambda rows: rows[2].update(reason="invalid_amount")),
            "changed-source": lambda: (root / "data/hoa_don.csv").write_bytes(b"changed\n"),
            "nfd-output": lambda: change_rows(records, nfd),
            "utf8-bom": lambda: records.write_bytes(b"\xef\xbb\xbf" + records.read_bytes()),
            "invalid-utf8": lambda: records.write_bytes(b"\xff\n"),
            "deeply-nested-json": lambda: records.write_bytes(b"[" * 2000 + b"0" + b"]" * 2000),
            "duplicate-json-key": duplicate_key,
            "extra-field": lambda: change_rows(records, lambda rows: rows[0].update(extra=True)),
            "wrong-order": lambda: change_rows(records, lambda rows: rows.reverse()),
            "oversized-artifact": lambda: records.write_bytes(b" " * (1024 * 1024 + 1)),
            "symlink-artifact": lambda: (records.unlink(), records.symlink_to(errors)),
        }
    if task_id != "b002-unicode-files":
        raise ValueError("Unregistered legacy controls: " + task_id)
    index = root / "output/index.jsonl"
    files = root / "output/files"
    def rows():
        return load_rows(index)
    def missing_nfd():
        values = rows()
        item = next(row for row in values if not unicodedata.is_normalized("NFC", row["source"]))
        (files / item["target"]).unlink()
        save_rows(index, [row for row in values if row is not item])
    def overwrite():
        values = rows()
        (files / values[1]["target"]).write_bytes((files / values[0]["target"]).read_bytes())
    def strip_filename():
        item = rows()[0]
        name = "".join(c for c in unicodedata.normalize("NFD", item["target"]) if not unicodedata.combining(c))
        (files / item["target"]).rename(files / name)
    def wrong_space():
        item = next(row for row in rows() if " " in row["source"])
        (files / item["target"]).rename(files / item["target"].replace(" ", "_"))
    def symlink_file():
        item = rows()[0]
        path = files / item["target"]
        path.unlink()
        path.symlink_to(root / "incoming" / item["source"])
    return {
        "missing-nfd": missing_nfd,
        "lost-file": lambda: (files / rows()[0]["target"]).unlink(),
        "overwritten-file": overwrite,
        "strip-filename-accents": strip_filename,
        "wrong-filename-space": wrong_space,
        "wrong-hash": lambda: change_rows(index, lambda values: values[0].update(sha256="0" * 64)),
        "string-size": lambda: change_rows(index, lambda values: values[0].update(size_bytes="1")),
        "wrong-source-form": lambda: change_rows(index, lambda values: values[0].update(source=unicodedata.normalize("NFC", values[0]["source"]))),
        "wrong-order": lambda: change_rows(index, lambda values: values.reverse()),
        "changed-source": lambda: (root / "incoming" / rows()[0]["source"]).write_bytes(b"changed"),
        "extra-file": lambda: (files / "extra.txt").write_bytes(b"extra"),
        "empty-index": lambda: index.write_bytes(b""),
        "deeply-nested-json": lambda: index.write_bytes(b"[" * 2000 + b"0" + b"]" * 2000),
        "missing-index": lambda: index.unlink(),
        "utf8-bom": lambda: index.write_bytes(b"\xef\xbb\xbf" + index.read_bytes()),
        "symlink-file": symlink_file,
    }


