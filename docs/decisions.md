# Nhật ký quyết định

| Ngày | Quyết định | Lý do |
|---|---|---|
| 12/11/2026 | Bắt đầu M1 bằng hai task artifact B | Hoàn thiện verifier trước khi mở rộng |
| 12/11/2026 | Dùng Harbor 0.25.0, schema 1.4 | Kiểm tra tài liệu và bản phát hành hiện hành trước triển khai |
| 12/11/2026 | Python 3.12, Linux container, thư viện chuẩn | Giảm phụ thuộc, tái lập Unicode; Windows Python chỉ hỗ trợ kiểm tra cấu trúc |
| 12/11/2026 | B001 số nguyên VND, ngày d/m đủ hai chữ số | Tách khỏi task thập phân/làm tròn tương lai |
| 12/11/2026 | B002 copy file và lập index, prefix số thứ tự | Va chạm NFC được giải quyết xác định, giữ nguyên nguồn |
| 12/11/2026 | Verifier chỉ đọc artifact, không thực thi submission | Hai task đầu không cần chạy code agent; giảm bề mặt can thiệp |
| 12/11/2026 | Chưa chạy model có phí, chưa nhập task A | Người dùng xác nhận chưa có baseline/model/ngân sách |
| 12/11/2026 | Tắt mạng tĩnh bằng Compose cho cả agent và verifier | Lần chạy Harbor đầu từ chối policy no-network do kernel/backend egress; không bật mạng để vượt lỗi |
| 12/11/2026 | Lưu jobs/artifact ở filesystem Linux, không trên ổ D | Oracle B002 bị chấm sai khi artifact có tên khác hoa/thường đi qua Windows; wrapper chặn jobs-dir dưới /mnt |

## Vấn đề còn mở

Quy ước hash payload hiện tại: sắp đường dẫn tương đối POSIX theo code point, không sắp đối tượng Path phụ thuộc OS. Có regression Windows/Linux; hash này khớp run manifest Linux đã lập trước, không thay đổi task. Báo cáo snapshot M1 gốc giữ nguyên lịch sử; native-six và review records dùng canonical hash.

Cập nhật giai đoạn 2 ngày 12/11/2026: native-six kỹ thuật đã hoàn thành. Registry tường minh, run manifest lập trước, adapter Harbor0.25.0 và CI family-bootstrap đã triển khai. B005 dùng Node22.14.0/ICU76.1/CLDR46.0 khóa image digest, Linux amd64. Mọi task mới tiếp tục chấm artifact-only. Hồ sơ review vẫn pending. Hai outlier pha verifier repeat 1 chưa rõ nguyên nhân; cần điều tra trước pilot model. Xem reports/native-six-validation.md và reports/pilot-readiness.md.

- Snapshot/cấu hình tiếng Anh từ đội Eval; xem `eval-input-checklist.md`.
- Reviewer kỹ sư Việt Nam độc lập: chưa có; không tự nhận đã review.
- Giấy phép phát hành nội dung tự xây: chủ dự án chưa quyết định; chưa cấp license thay chủ dự án.
- Chọn model/agent/ngân sách và chính sách kết nối API cho model run.
- Split công khai/kín và phân bổ task sau pilot.
- Đã khóa dependency trong uv.lock và image digest trong Dockerfile; khi thay đổi phải kiểm định và ghi provenance mới, không suy từ việc đọc tài liệu.

## Cập nhật giai đoạn 3 — 12/11/2026

Giữ nguyên task/image/library và bằng chứng cũ. Default WSL socket bị timeout trong Python/socket probes dù Windows API và Desktop proxy hoạt động; một direct probe trả nhanh, chưa đủ kết luận hồi phục. Dùng relay Unix command-only mode0600, target user thường, không restart dịch vụ hoặc sửa socket hệ thống.4 smoke B005/B006 pass,41 test Linux; default preflight sau đó vẫn fail.

Preflight có bước/timing/deadline và owned subprocess cleanup, executor validation giữ oracle/nop-only và job deadline. Template model/dry-run72 trial không executable, không đọc secret/API; real agent mapping và budgets vẫn thiếu. Private split mới chỉ thiết kế theo family. Xem reports/stage3-readiness.md để biết điều kiện hiện tại, không coi lịch sử smoke thành readiness model.
