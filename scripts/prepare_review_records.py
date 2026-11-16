"""Prepare empty review records; never claim an independent review occurred."""
import hashlib
from pathlib import Path
from dev_registry import manifest
from materialize_variants import payload_hash


def prepare(repo):
    folder=repo/'reports/reviews';folder.mkdir(parents=True,exist_ok=True)
    for row in manifest():
        target=folder/(row['task_id']+'.md')
        if target.exists():continue
        task=repo/'tasks'/row['task_id']
        instruction=hashlib.sha256((task/'instruction.md').read_bytes()).hexdigest()
        target.write_text(f"""# Hồ sơ review — {row['task_id']}

- Task version: {row['task_version']}.
- Payload SHA-256: `{payload_hash(task)}`.
- Instruction VI SHA-256: `{instruction}`.
- Trạng thái: **pending**; chưa thực hiện review độc lập.
- Reviewer: chưa chỉ định.
- Ngày review: chưa có.
- Thời gian giải thực đo: chưa đo.
- Quyết định: chưa có; không coi việc tạo hồ sơ là accepted.

## Checklist cần người review thực hiện

- [ ] Giải trước khi xem oracle/expected và ghi thời gian.
- [ ] Đối chiếu ràng buộc EN/VI, schema, locale và trường hợp lỗi.
- [ ] Kiểm tra expected tĩnh bằng phương pháp độc lập.
- [ ] Thử lời giải hợp lệ khác, false positive/negative và dữ liệu biên.
- [ ] Kiểm tra môi trường, source/answer separation và artifact transfer.
- [ ] Ghi nhận xét, lỗi, quyết định và cập nhật review_status đúng snapshot.

## Nhận xét và bằng chứng

Chưa có. Xem [review guide](../../docs/review-guide.md) và [thiết kế task](../../docs/native-six-design.md).
""",encoding='utf-8')
    print('Review templates prepared; all remain pending')


if __name__=='__main__':prepare(Path(__file__).resolve().parents[1])
