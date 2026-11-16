# Kiểm định credential loader offline

Cập nhật 13/11/2026. Bộ regression trên Linux/WSL bằng Python 3.12.16 đạt **150/150 test**, 0 failure/error/skip. Trong đó có **24 test mới** về credential scope, redaction và artifact policy. Không có model/API call thật hoặc SDK client thật được khởi tạo.

## Kết quả kiểm định

| Hành vi | Bằng chứng |
|---|---|
| Preview/dry-run, target không được phép, gate fail | Bị từ chối trước file/environment read |
| Gate phát sinh exception | Chỉ trả lỗi cố định; không chain message chứa token giả |
| Environment ưu tiên | Không đọc fallback `.env`; biến có mặt nhưng rỗng thì fail |
| Encoding và syntax | UTF-8 BOM/CRLF/quote và path tiếng Việt hoạt động; duplicate/shell/interpolation bị từ chối |
| Environment toàn cục | Không bị sửa khi mở/đóng credential scope |
| Child process | Chỉ nhận key giả và public env allowlist; secret khác không được kế thừa |
| Repr/JSON/error | Không xuất giá trị; SDK exception message không được serialize |
| Đóng scope/gate thay đổi | Truy cập sau close hoặc sau gate fail bị chặn |
| Native source snapshot | `.env` thật không nằm trong 190 input file đã hash/copy |
| Artifact fixture | Dotenv private, symlink, outside path và example có giá trị bị từ chối; bundle hợp lệ không có token giả |
| Metadata CLI | Kiểm file/Git/source policy mà không đọc credential value |

Test symlink đã chạy trên Linux; lần kiểm nhanh trên Windows bỏ qua test đó, vì vậy dùng bộ Linux hoàn tất làm bằng chứng chính. Không đặt trước số test cần đạt; 150 là count thực của report.

## Key thật và source đã bảo toàn

[Inventory](stage8-input-state.json) ghi `.env` có mặt, được Git ignore, chưa track và auth chưa kiểm. [Metadata CLI](stage8-credential-status.json) xác nhận `credential_value_read=false`; không lưu giá trị, hash hoặc chiều dài key.

Các test chỉ đọc fixture credential do chính test tạo trong temp directory/mapping. Runner bootstrap không source `.env`; source policy chạy trước khi native harness đọc bytes. Không thêm SDK/dependency provider khi chưa có agent/model được chọn. Snapshot/task/source/report giai đoạn trước giữ nguyên; các guard model và ledger SIM_USD cũ tiếp tục hoạt động.

## Bằng chứng và giới hạn

- [Test Linux và input hashes](stage8-unit-tests.json).
- [Metadata credential](stage8-credential-status.json).
- [Tài liệu loader](../docs/credential-loading.md).
- [Readiness bàn giao](stage8-readiness.md).

Loader không xác thực key, model access, quota hoặc budget. Chưa có provider/agent factory thực nối vào helper; callback gate trong test chỉ là stub cho kiểm định. Repr/JSON/redaction không ngăn caller cố tình log string từ `sdk_key()`, không xóa được mọi bản sao bộ nhớ và không thu hồi key đã cấp cho process con. Các giới hạn này cần được tính trong binding/lifecycle thực.

G8.1 đạt cho việc lưu credential; phần loader độc lập của V2 đã kiểm offline. **G8.2 chưa hoàn tất**, G8.3 chưa kiểm định, G8.4–G8.5 chưa chạy vì cấu hình agent/model/budget/runtime và review vẫn thiếu.
