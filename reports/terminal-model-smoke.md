# Terminal model smoke — chưa chạy

Cập nhật 13/11/2026. Không có terminal trial model thật, reward model hoặc raw model trajectory mới. Hai trial EN/VI ở đây mới là kế hoạch, không phải coverage đã thực hiện.

| Planned trial | Task | Trạng thái | Reward model |
|---|---|---|---|
| B001 / EN / cấu hình host-terminal | `b001-vn-invoice` | Chưa gửi | Chưa có |
| B001 / VI / cấu hình host-terminal | `b001-vn-invoice` | Chưa gửi | Chưa có |

Người dùng xác nhận chưa có reviewer. [Gói mở đầu](reviews/stage10-b001-opening.zip) đã có instruction, CSV gốc và hồ sơ pending, không có oracle/expected/grader. Runtime WSL/Docker hiện fail; scope/caps/compute cho smoke chưa chốt. [Run spec](stage10-run-spec.md) vẫn draft; CLI mặc định preview và execute với draft bị từ chối trước đọc key/tạo container.

Đã có [kiểm định kỹ thuật offline](terminal-agent-offline-validation.md), gồm hai fixture có grader reward 0/0. Các kết quả fixture không đưa vào bảng reward model. Request OpenAI thật giai đoạn 9 vẫn chỉ chứng minh [provider connectivity](provider-connectivity.md).

Controller lifecycle, worker deadline và compute revision đã có kiểm offline. Khi có reviewer/runtime và scope budget hợp lệ, kiểm backend/container thật, đóng băng approved config/ledger path/quote và capture attestation mới trước dispatch. Không gửi lại connectivity để thay thế bước này.
