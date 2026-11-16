"""Create visually similar but byte-distinct filenames inside Linux."""
import argparse
import unicodedata
from pathlib import Path


def generate(root: Path) -> None:
    incoming = root / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    fixtures = [
        ("Báo cáo.txt", "Dữ liệu NFC\n".encode("utf-8")),
        (unicodedata.normalize("NFD", "Báo cáo.txt"), "Dữ liệu NFD khác\n".encode("utf-8")),
        ("báo cáo.txt", b"lowercase\n"),
        ("Đơn hàng.csv", "mã,số lượng\nA,2\n".encode("utf-8")),
        ("khách hàng 01.txt", b"spaces in filename\n"),
        ("ảnh mẫu.txt", bytes([0, 1, 2, 255, 10])),
    ]
    for name, content in fixtures:
        (incoming / name).write_bytes(content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/app"))
    generate(parser.parse_args().root)
