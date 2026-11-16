# Run spec giai đoạn 11 — bản nhỏ nội bộ đã chạy

Ngày 13/11/2026. Đích do người dùng chốt: sáu task B, một cấu hình, EN/VI, ba repeat. [Manifest](stage11-batch-plan.json) được freeze trước batch; [config](../configs/development-benchmark.json) ghi quyền thực hiện plan 11 và trần kiểm thử 2 USD có từ hội thoại, không phát sinh yêu cầu cung cấp lại key/model/budget.

| Thành phần | Giá trị thực |
|---|---|
| Run chính / scope | `stage11-development-001` / `development-batch` |
| Trial | 36, một cấu hình, repeat 1–3; seed 20261113 |
| Model | `gpt-5.4-mini-2026-03-17`, reasoning none, Responses/function terminal |
| Limits | Sáu request/trial, 2.048 output token, payload 64 KiB, trial 300s, command 10s |
| Runtime | `desktop-shared-relay-v2`, Ubuntu-22.04, user tamle, Docker Linux; không sửa socket hệ thống |
| Agent/verifier | Riêng container, network none; root read-only, tmpfs bounded; không key/oracle/test kín/socket trong agent |
| Task B005 | Node 22.14.0, ICU 76.1, CLDR 46.0 được kiểm thực |
| Ledger | `/home/tamle/vi-terminal-bench-stage11/ledger.sqlite3`, persistent pool 2 USD |
| Settlement | `observed-usage-conservative-input-v1`; chỉ hoàn reserve khi usage/price mapping đủ; margin 0,10 USD |
| Compute | Local, not-metered; có thời gian/resource, không ép quote cloud |
| Review | Pending được phép trong development; không thay human acceptance, author hoặc gate pilot cũ |
| Smoke | Hai run riêng: bốn trial B001; smoke002 cùng source/config cuối đã đạt trước batch |

Source của run đầu smoke giữ trong [snapshot](stage11-smoke-initial-source.zip); sửa phần nối report/manifest rồi kiểm lại bằng smoke002, không dùng smoke cũ để điền coverage batch. Mọi token/cost của cả hai smoke đều tính vào shared pool.

Batch tạm dừng một lần do CredentialError DISPATCH_BLOCKED trước HTTP worker. [Recovery có audit](stage11-pre-dispatch-cancellation.json) giữ checkpoint, raw data và mọi request đã tính phí; chỉ re-arm intent chưa dispatch, không replay lời giải sai. Probe thấy attestation thời gian từ chối tạm thời; pin controller CPU 0 đạt 10/10 probe, phần tiếp tục hoàn tất. Root cause clock tổng quát chưa được khẳng định; default Ubuntu proxy vẫn không được coi đã sửa triệt để.

Chạy thực giữ model/task/prompt/tools/image/limits không đổi. Bản freeze chứa critical source; recovery utility được bổ sung sau freeze, có hash riêng trong audit và không thay critical execution source. [Report](development-benchmark-results.md) ghi điểm và chi phí, [quickstart](../docs/development-benchmark-quickstart.md) là entrypoint tái lập.
