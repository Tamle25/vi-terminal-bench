# Run spec giai đoạn 9 — provider connectivity

Ngày chốt: 13/11/2026, Asia/Saigon. Người dùng ủy quyền chọn model và cho phép kiểm tra với tổng trần **2 USD**. Đây là phạm vi thực thi đã được cấp trong hội thoại.

| Trường | Giá trị đóng băng |
|---|---|
| Run ID / scope | `stage9-openai-connectivity-001` / `provider-connectivity` |
| Provider / model | OpenAI / `gpt-5.4-mini-2026-03-17` |
| Endpoint | HTTPS `api.openai.com`, POST `/v1/responses` |
| Client | `provider_connectivity_v1.py`, Python stdlib `http.client`, không SDK phụ thuộc |
| Request | Một câu tiếng Việt công khai, không có dữ liệu benchmark; nội dung chính xác trong [config](../configs/stage9-connectivity.json) |
| Limits | 1 attempt tối đa; 128 output token; reasoning `none`; timeout socket 30 giây; không stream, tool, retry, redirect hoặc fallback model |
| Service tier | `default`; `store=false` |
| Credential | `.env` cục bộ, chỉ qua scoped loader sau kiểm gate; không lấy key từ argv hoặc snapshot |
| Account reference | `local-dotenv-user-provided-project-key`: tên nguồn credential thực; chưa xác minh OpenAI project ID/account ownership |
| Budget | Trần đợt kiểm tra 2,00 USD; reservation 0,01 USD; chỉ cho phép run này, không tự mở run khác |
| Ledger | `jobs/stage9-connectivity/ledger.sqlite3`, namespace USD riêng; không dùng SIM_USD |
| Invoice | Chưa có đối chiếu hóa đơn; token-price estimate và exposure được lưu riêng |

Model được chọn vì có bản snapshot cố định, hỗ trợ lập trình và Responses API. Giá standard được kiểm từ [OpenAI Docs](https://developers.openai.com/api/docs/models/gpt-5.4-mini) ngày 13/11/2026: input 0,75 USD, cached input 0,075 USD, output 4,50 USD trên một triệu token. `service_tier=default` dùng giá standard theo [API reference](https://developers.openai.com/api/reference/resources/responses/methods/create).

Reservation dùng giả định thận trọng 4.096 input token cho prompt ngắn và 128 output token, tương đương 0,003648 USD theo đơn giá trên, làm tròn lên 0,01 USD. Đây là giới hạn phía runner cho run này, không phải thiết lập trần chi tiêu toàn tài khoản OpenAI. Không có request phụ để liệt kê model hoặc kiểm key trước request đã chốt.

Đầu vào và source hash nằm trong [manifest](stage9-frozen-inputs.json). Unique claim được commit trước khi đọc credential; `submitted` được commit trước network sink. Claim đã có sẽ chặn thực thi lại, kể cả khi timeout, lỗi credential hoặc crash. Không xóa DB để retry. Nếu export lỗi sau khi đã lưu receipt vào DB, dùng `--export` vào đường artifact còn trống; export không gửi request. DB còn `submitted` mà thiếu receipt phải điều tra thủ công, không resend.

Response được giới hạn kích thước và chỉ lưu các field cần thiết qua redaction. Không lưu Authorization/header tùy ý. Thiếu usage/model/tier phù hợp sẽ giữ cost `null`; không coi lỗi HTTP là miễn phí. Reservation vẫn giữ 0,01 USD đến khi đối chiếu hóa đơn; estimate không phải khoản phí mới được cộng thêm reservation.

Gate kết nối không mở gate benchmark. Agent terminal, task review và runtime cho smoke chưa đủ bằng chứng. Hai cấu hình so sánh, ngân sách pilot và review 6/6 vẫn cần trước pilot 72 trial. Không có quyền dùng trọn 2 USD để tự chạy benchmark hoặc thử hàng loạt model.
