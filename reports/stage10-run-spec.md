# Run spec draft — smoke B001

Ngày 13/11/2026. Trạng thái **draft, dispatch disabled**; chưa có request smoke. Kế thừa [giai đoạn 9](stage9-summary.json) và [kế hoạch 10](../Plan/plan-giai-doan-10.md).

| Trường | Lựa chọn hiện tại |
|---|---|
| Run / scope | `stage10-b001-smoke-001` / `model-smoke` |
| Agent | `vi-host-terminal/0.1`, host loop stdlib, terminal tool trong Docker |
| Provider/model | OpenAI Responses / `gpt-5.4-mini-2026-03-17` |
| Task/trial | B001 × EN/VI × một lần × một cấu hình = hai planned trial |
| Thứ tự | EN trước, VI sau; workspace/history độc lập |
| Retry/concurrency | Không retry tự động; concurrency 1 |
| Request/output | Tối đa 4 request/trial; 1.024 output token/request |
| Input reservation | Toàn bộ maximum input model 272.000 token/request; payload thực tối đa 16 KiB |
| Lệnh/artifact | Lệnh 10 giây, capture 16 KiB/luồng; artifact 16 MiB, tối đa 4.096 tar member |
| Runtime | Chưa chọn: default WSL Docker fail; không chuyển endpoint/relay hoặc restart dịch vụ |
| Review | Người dùng xác nhận chưa có reviewer; kit pending, acceptance 0/6 |
| Account | Nguồn key đã cung cấp cục bộ; project ID của provider chưa xác minh |
| Pool/caps/authorization | Chưa có cho smoke; trường tương ứng giữ null trong config |
| Compute / storage ledger | Chưa có quote/rate/charge evidence hoặc persistent ledger path được chốt; chưa coi local compute là 0 USD |

[Config draft](../configs/stage10-smoke.draft.json) có kind `draft-not-authorized`; không dùng làm approved manifest. Một cấu hình smoke không điền vào template pilot hai model. Số request giảm từ đề xuất ban đầu tám xuống bốn/trial sau tính reservation; đây là lựa chọn kỹ thuật để chuẩn bị scope nhỏ.

Theo [OpenAI Docs](https://developers.openai.com/api/docs/models/gpt-5.4-mini), kiểm ngày 13/11/2026: `(272.000 × 0,75 + 1.024 × 4,50) / 1.000.000 = 0,208608 USD/request`. Tám request tối đa là **1,668864 USD inference**. Cộng exposure connectivity còn giữ 0,01 USD thành **1,678864 USD**, chưa compute. Đây là ước tính dự phòng, không phải phí đã chi hoặc quyền dùng phần dư của trần cũ.

Đề xuất để chủ dự án xem xét sau khi đủ review/runtime: cap inference 1,70 USD và compute không quá 0,10 USD, cùng exposure cũ 0,01 USD là 1,81 USD; vẫn cần xác minh compute reservation/đơn giá, quyền scope smoke và tổng pool trước khi điền thành approved config. Không có khoản chi nào được cấp chỉ bằng đoạn đề xuất này. Không yêu cầu quyết định thêm trong lúc reviewer/runtime vẫn chưa đủ để chạy.

Controller CLI, worker HTTP có deadline ở parent, image provenance và compute revision đã được bổ sung và kiểm offline. Trước dispatch còn cần: review B001 accepted đúng snapshot; runtime được chọn và Docker thực đạt; lifecycle/worker được kiểm với backend thực; image/task/source/provenance đóng băng; pool/caps/compute quote và persistent ledger path đủ cơ sở; authorization áp dụng smoke; attestation mới cho run. Không gửi một request connectivity khác để thay thế các bước này.
