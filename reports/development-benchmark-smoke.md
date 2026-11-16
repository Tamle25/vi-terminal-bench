# Smoke model thật — giai đoạn 11

Hai lần smoke riêng của B001 đều có hai trial EN/VI, artifact do model tạo, terminal trajectory và verifier thật. Cả bốn trial đạt reward 1; các trial này không được cộng vào coverage batch 36 trial.

| Run | Trial hợp lệ | Response provider | Estimate token bảo thủ (USD) |
|---|---:|---:|---:|
| stage11-smoke-001 | 2/2 | 5 | 0,01146075 |
| stage11-smoke-002 | 2/2 | 4 | 0,009603 |

Smoke002 dùng cùng source/config đã freeze cho batch. Smoke001 giữ riêng source snapshot trước sửa liên kết plan trong report; không trộn source hai lần chạy hoặc bỏ chi phí của lần trước. Các estimate chưa phải invoice; compute local chưa đo phí.

Evidence: [smoke001](stage11-smoke-001-summary.json), [smoke002](stage11-smoke-002-summary.json), [plan smoke002](stage11-smoke-plan.json), [source smoke001](stage11-smoke-initial-source.zip), [usage](stage11-usage-and-budget.json), [archive raw Linux](stage11-native-evidence.tar.gz).

`technical_smoke_passed` áp dụng cho summary scope `development-smoke`. Field này bằng false trong summary scope `development-batch` không phủ định smoke đã đạt; batch được mở bằng evidence smoke002 và đối chiếu ledger. Kết quả cuối xem [báo cáo batch](development-benchmark-results.md).
