# Ledger ngân sách chung — giai đoạn 6

Trạng thái: đã triển khai và kiểm định trong phạm vi **offline fixture, SIM_USD**. Chưa có billing account/provider thực hoặc bảng giá thật; code từ chối pool currency USD. Không có API client, secret loader hoặc tự động chuyển fixture thành thực thi model.

## Hợp đồng và cấu trúc

`billing_ledger.py` quản lý SQLite WAL, `synchronous=FULL`, foreign key và transaction `BEGIN IMMEDIATE`. Một DB có thể chứa nhiều pool độc lập. `billing_scope_id` xác định pool dùng chung, `account_ref` là reference không chứa secret; việc ánh xạ tới account thực vẫn cần quyết định và kiểm định riêng.

Pool schema `vi-billing-pool/0.1` có origin/currency/unit, caps inference/compute và policy `block-pool`. Run đăng ký scope smoke/pilot, manifest hash và caps riêng. Metadata này đóng băng; balance và receipt revision thay đổi không làm thành cấu hình model mới.

| Bảng | Vai trò |
|---|---|
| `pools`, `runs` | Định danh, currency và caps đóng băng |
| `requests` | Identity đầy đủ, reservation, phase, owner và actual cost |
| `receipts` | Envelope/raw evidence của mọi revision, chain hash |
| `holds` | External uncertainty, chỉ gỡ bằng cập nhật có nguồn |
| `events` | Lịch sử nghiệp vụ append-only theo đường code |

Event log hỗ trợ audit, không phải cơ chế chống người có quyền sửa SQLite. Hai DB khác nhau dù dùng cùng reference ID không được coi là cùng binding: bridge kiểm pool spec hash, run manifest, caps và scope với context local đã đóng băng.

## Reservation và số dư

Reservation được kiểm nguyên tử với cả trần pool và trần run. Cùng request identity đăng ký lại trả bản ghi cũ; khác identity/bound bị từ chối. Một receipt nhập lại không cộng phí lần nữa.

Các request reserved/submitted giữ reservation. Uncertain giữ exposure bảo thủ theo reservation và actual đã biết. Request submitted/uncertain hoặc external hold chặn dispatch mới trong pool; claim cũng kiểm lại trạng thái/caps. Pool khác độc lập tiếp tục được kiểm theo budget của chính nó. Fixture binding hiện thực thi C1 tại pool.

Actual cost 0 khác null. Null không trở thành miễn phí; known subtotal, số request chưa rõ cost và exposure được báo riêng. Điều chỉnh phí phải có revision có nguồn và lý do; không được xóa phí đã biết thành null. Actual vượt cap vẫn lưu đúng và chặn request mới; không đảo ngược phí đã phát sinh.

Đơn vị là số nguyên micro-unit, không nhận bool/float cho amount; request phải có reservation khác 0 trước dispatch. Đây không phải estimate giá API thực. Hệ thống chưa cộng nhiều currency, quy đổi tỷ giá hoặc đọc provider account balance.

## Outbox giữa local DB và ledger chung

`BillingExecutor` và `BillingFixtureAdapter` kế thừa đường executor đã có, không sửa source hay archive giai đoạn 5. Local plan mới gắn manifest, pool spec và hash source billing. Bridge bổ sung `billing_outbox`, `billing_overlay`, `billing_context` vào state mới.

Trình tự:

1. Local request intent/claim được persist; outbox ghi identity trước khi reserve vào ledger chung.
2. Global reservation kiểm pool/run; global claim phải thành công trước khi gửi fake provider.
3. Receipt ghi vào ledger chung theo revision; sau đó sync overlay và request local.
4. Nếu process ngắt giữa hai DB, outbox và global identity cho phép đối chiếu/replay. Không coi hai commit này là nguyên tử.

Crash sau global reserve giữ reservation; crash sau claim không có receipt giữ pending/uncertain. Không tự release theo lease hoặc negative lookup. Chỉ global reservation chưa claim mới được cancel; việc cancel không tự gán reward hoặc chạy lại partial task.

## Phí điều chỉnh và dữ liệu task

Kết quả task đã biết được giữ nguyên qua billing correction. Với receipt còn unknown, sync có thể bổ sung cost và settle một kết quả đầy đủ. Với task/raw đã settled, revision phí nằm ở overlay và ledger chung; không viết lại raw task cũ.

Vì vậy, sau adjustment cần phân biệt:

- Legacy task accounting: giá trị lúc task được settle, dùng để truy nguyên raw.
- Authoritative billing: revision hiện tại của ledger chung, overlay, known subtotal và exposure.

`export/shared-billing.json` cung cấp binding/source, outbox, overlay, phí đã biết và unknown count. `trials.jsonl` legacy vẫn giữ `cost_usd=null`; phí SIM_USD lúc settle không tự được coi là hóa đơn cuối sau correction. Khi tổng hợp tài chính phải dùng ledger/overlay và chỉ rõ delta; không cộng cả base fee lẫn toàn bộ revision mới.

## Kiểm định và giới hạn

Đã có test cạnh tranh giữa hai run, cap run/pool, external hold, duplicate receipt, raw hash/identity conflict, overrun, zero/null, cancel trước claim, crash outbox, CLI import/replay, read-only status và restore dữ liệu. Xem [báo cáo giai đoạn 6](../reports/stage6-readiness.md).

Chưa kiểm account/provider thực, SDK retry, giá/usage, isolation hoặc remote lookup/cancellation. Partial multi-request thiếu checkpoint giữ uncertain; không có tự động tái tạo trạng thái agent. Binding model hiện vẫn vắng mặt; các field/receipt JSON không cấp quyền dispatch.
