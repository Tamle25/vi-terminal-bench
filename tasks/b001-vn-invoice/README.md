# b001-vn-invoice — Task card

- Track B; family `vn-invoice`; version 0.1.0; primary skill `number-date`.
- Độ khó dự kiến: easy; chưa hiệu chỉnh bằng model. Ước lượng chuyên gia: 20–40 phút, chưa đo.
- Tình huống: chuẩn hóa xuất hóa đơn từ CSV sang JSONL.
- Fixture: 12 hóa đơn tổng hợp, 6 hợp lệ và 6 lỗi. Có NFD, tên có dấu phẩy, ngày nhuận, số 0 và số tiền phân nhóm.
- Đầu ra: `output/hoa_don.jsonl`, `output/errors.jsonl`; nguồn giữ nguyên.
- Oracle: `solution/solve.py`; đáp án cố định trong `tests/expected.json`, không dùng oracle để tính expected khi chấm.
- Mutants: no-op, rỗng, thiếu dòng, bỏ dấu, đảo ngày/tháng, sai tiền, kiểu tiền sai, thiếu lỗi, đổi nguồn, NFD đầu ra, BOM, duplicate key, boolean thay số 0.
- Cách giải khác: dùng đáp án cấu trúc độc lập với key order khác để kiểm tra việc chấp nhận artifact hợp lệ. Chưa thay thế review của người độc lập.
- Nguồn: tự tạo, không lấy task bên ngoài; license phát hành chờ chủ dự án.
- Tác giả: Codex trong phiên triển khai; reviewer độc lập: chưa có. Trạng thái: development.
