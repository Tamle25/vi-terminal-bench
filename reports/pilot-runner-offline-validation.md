# Kiểm định runner offline — giai đoạn 4

Kết quả ngày 12/11/2026: hoàn tất **72 trial mô phỏng**, 74 lượt fake dispatch với 74 request ID riêng; **0 model call** và không đọc secret. Đây là kiểm định hạ tầng điều phối, không phải kết quả benchmark model.

| Kiểm tra thực hiện | Kết quả |
|---|---|
| Phạm vi | 6 task × 2 instruction × 3 repeat × 2 cấu hình giả = 72 |
| Dừng sau tiến trình đầu | 11 dispatch, state đã ghi bền vững |
| Tiến trình thứ hai | Resume và hoàn tất 72 kết quả cuối |
| Tiến trình thứ ba | Không tăng dispatch |
| Retry | Một lỗi infra, một lỗi verifier; giữ cả phí hai attempt đầu |
| Agent failure | Một fixture reward 0, không retry |
| Raw → normalized → aggregate | 74 attempt, 72 final; coverage đủ trong namespace simulation |
| Ledger | 72.950 inference và 7.350 compute micro-unit SIM_USD |
| Unknown cost sau run này | 0; chi phí USD thực vẫn null |
| Khôi phục archive | Mở lại ledger/provider; 72 final và 74 dispatch khớp |
| Bộ test Linux/WSL | 70/70 đạt, 0 skip, 0 failure/error |

Run 72 trial chạy bằng Python 3.11 cục bộ trên Windows với SQLite, không dùng Docker. Bộ test đầy đủ chạy riêng bằng Python 3.12.16 trên Linux/WSL. Các test capture runtime sử dụng preflight fixture, không probe Docker thật. Không dùng kết quả này để xác nhận default WSL socket đã được sửa hoặc model runtime đã sẵn sàng.

Các test bổ sung kiểm tra crash sau reserve/submit/provider receipt, crash thật qua child process, lease/reconciliation, double-start và hai worker tranh claim, null reward, unknown cost, cap exhaustion/overrun, retry tối đa hai lần, plan drift, gate thiếu từng điều kiện và ngăn trộn simulation/model. Fake provider ghi mọi invocation trước xử lý request ID nên số request unique không che dispatch lặp. Trong lúc kiểm định đã sửa connection không đóng khi constructor từ chối resume sai plan.

Bằng chứng máy đọc:

- [Kết quả offline](stage4-offline-summary.json), [test Linux](stage4-unit-tests.json).
- [Plan mô phỏng](stage4-simulation-run.json), [scenario](stage4-simulation-scenarios.json).
- [Normalized attempts](stage4-simulation-trials.jsonl), [aggregate giả lập](stage4-simulation-results.json).
- [Archive state/raw/events](../jobs/stage4-offline-simulation.tar.gz).

SHA-256 archive: `51b85b9657f3b1eed93d3e005f3b1a0badd6c57ec442bf683f3fc72ae4bb45e2`.

Giới hạn: test lỗi provider, receipt có tính authoritative và đơn vị tiền đều là fixture. Chưa có kiểm định provider thật, phân loại rate limit thật, giá/usage thật, API isolation hay model dispatch. Giao thức retry/resume phải được nối với adapter thực và kiểm định lại trước smoke. Sáu task vẫn là development, review độc lập 0/6; không ước lượng năng lực model hoặc CI từ các reward giả.
