# Readiness — bản nhỏ development đã dùng được

Cập nhật 13/11/2026: **đã đạt mục tiêu bản nhỏ dùng được**. Có sáu task B, CLI, model thực, 36/36 trial hợp lệ, báo cáo tái lập và archive Linux đã kiểm restore. **35/36 pass**, EN 94,44%, VI 100%; một fail agent được giữ nguyên.

| Mốc | Trạng thái | Evidence |
|---|---|---|
| G11.1 — Runtime/development gate | Đạt cho runtime đã chọn | Relay v2 + workload user thường; pending review chỉ được phép trong development; không đổi guard reviewed pilot |
| G11.2 — Backend sáu task | Đạt | 6 oracle reward 1, 6 no-op reward 0; artifact/verifier riêng, B005 runtime đúng bản khóa |
| G11.3 — Smoke model | Đạt | B001 EN/VI có terminal trajectory, artifact/verifier/usage/cost thật; smoke002 cùng source/config batch |
| G11.4 — Bản nhỏ | Đạt | Đủ 36 trial, một cấu hình, EN/VI, ba repeat; JSON/CSV/Markdown và quickstart |

Kiểm cuối đạt **223/223 test Linux**, không skip. Report dựng lại từ outcome/ledger khớp JSONL/CSV/Markdown byte-for-byte. `resume-unstarted` sau khi run hoàn tất không tạo thêm request. Archive khôi phục đúng hash 604 file, ledger và dữ liệu Unicode/case-distinct.

Chi phí token bảo thủ cộng dồn cả smoke và connectivity khoảng **0,1349925 USD**, dưới trần pool 2 USD. Estimate theo cached input là 0,1340421 USD; invoice chưa có, compute local not-metered. Hold/margin không được cộng thành fee. Không còn request uncertain trong ledger hiện tại; một intent trước HTTP đã được reconcile bằng proof/cancellation có audit, không release một request có thể đã billable.

Runtime dùng workaround explicit: shared Docker container proxy qua relay tạm, controller CPU 0. Default Ubuntu proxy từng timeout; clock attestation có jitter đã quan sát. Không tuyên bố đã sửa toàn bộ Docker/WSL hoặc timing controller là latency model thuần. Gate runtime/expiry/budget/source vẫn giữ; không có key/socket/đáp án trong agent/verifier.

Trạng thái dữ liệu: sáu task development, tác giả Codex-assisted, review **0/6 pending**; giấy phép task chờ chủ dự án. Human review không chặn bản nội bộ theo mục tiêu mới, nhưng kết quả này không được gắn nhãn reviewed pilot/phát hành. Phần A, mở rộng 30 task B và so sánh hai cấu hình chưa thuộc mốc đã hoàn thành.

Các tài liệu chính: [kết quả](development-benchmark-results.md), [quickstart](../docs/development-benchmark-quickstart.md), [run spec](stage11-run-spec.md), [summary](stage11-summary.json), [protocol development](../docs/development-benchmark-protocol.md). Các mốc reviewed model/pilot cũ không được tự đánh dấu hoàn tất bằng kết quả development này.
