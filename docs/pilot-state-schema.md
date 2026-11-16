# Hợp đồng trạng thái pilot

Phiên bản đầu: `0.1`. Đây là các hợp đồng kiểm tra tính nhất quán dữ liệu; không xác thực danh tính người review, không phải token cấp quyền gọi model.

## Trạng thái và định danh

| Trạng thái | Ý nghĩa |
|---|---|
| `pass` | Bằng chứng đáp ứng kiểm tra trong scope đã nêu |
| `fail` | Bằng chứng được cung cấp nhưng vi phạm hợp đồng |
| `missing_input` | Thiếu quyết định hoặc dữ liệu đầu vào |
| `unverified` | Chưa kiểm định bằng nguồn thực tế phù hợp |
| `not_applicable` | Không thuộc phạm vi lần thực hiện này |

`reports/stage4-input-state.json` ghi thời điểm UTC, scope, snapshot và inventory checksum. `vi-pilot-readiness/0.1` ghi run ID, snapshot ID, sáu điều kiện cùng lý do, nguồn bằng chứng và hành động tiếp theo. Bằng chứng khác scope không tạo ra một trạng thái pass cho pilot hiện tại.

`pilot_contracts.snapshot()` băm canonical JSON chứa version, tác giả, family, skill, payload và prompt EN/VI của sáu task. Review status và Docker health không nằm trong snapshot task. Payload bao gồm dữ liệu, environment, solution và verifier theo cùng thuật toán đã dùng ở các giai đoạn trước. Thay hợp đồng task phải tăng version; thay quan sát runtime không tăng version task.

## Runtime

Danh mục [runtime-profiles.json](../configs/runtime-profiles.json) có hai profile, nhưng `selected_runtime_profile` hiện là `null`. Fingerprint ổn định gồm ID/version, mode, distro/user, endpoint class, policy network/socket, timeout và concurrency đã kiểm định. Socket path ngẫu nhiên và timestamp chỉ xuất hiện trong observation.

`vi-runtime-attestation/0.1` phải có `kind=runtime-capture`, run/snapshot/profile ID, profile hash, `issued_at_utc`, `expires_at_utc`, preflight và observation. Thời hạn tối đa 900 giây, mặc định 300. Gate từ chối sai run, sai snapshot, hết hạn, thời điểm tương lai, concurrency vượt profile, endpoint khác loại hoặc preflight không đạt.

Native chỉ nhận Unix socket `/run/docker.sock` hoặc `/var/run/docker.sock`. Relay phải ở `/tmp/vi-bench-proxy-*/docker.sock`, mode `0600`, lifecycle `command-only`. Capture kiểm tra endpoint trước khi probe engine; không tự chọn relay, bật root hoặc sửa Docker. Relay capture còn kiểm tra owner/socket và ancestry của wrapper quản lý. Công cụ không phải bằng chứng mật mã hay cơ chế chống thay đổi môi trường sau capture. Trước dispatch thật cần adapter kiểm định isolation/egress và tái kiểm tra attestation; policy trong JSON không tự thực thi cách ly.

## Review

Input cho `review_records.py --records` là JSON array. Mỗi record có đúng các trường:

```text
task_id, task_version, payload_sha256, prompt_hashes,
reviewer, author, reviewer_kind, reviewed_at,
expert_time_sec, decision, notes
```

`prompt_hashes` chứa EN/VI; `reviewed_at` dùng `YYYY-MM-DD`; `expert_time_sec` là thời gian thực đo dương. `decision` là `accepted` hoặc `changes_requested`. Reviewer phải là người khác tác giả và `reviewer_kind=human`. Không lấy oracle pass hay nhận xét do AI tạo làm accepted.

Mặc định CLI chỉ kiểm tra và xuất coverage. `--apply` mới nhập accepted đã cung cấp vào manifest, tạo backup và thay file qua file tạm. Nó không nhập record sai hash hoặc tự tạo chấp nhận. Coverage đọc chính các record được cung cấp; khi chạy gate sau import vẫn truyền file record qua `--reviews`. Giữ file gốc như bằng chứng; manifest không thay thế bằng chứng review.

Hiện coverage là **0/6**. Hai archive review nằm trong inventory đầu giai đoạn; không được gửi ra ngoài trong đợt này. Người review mở public trước theo [hướng dẫn review](review-guide.md), sau đó đối chiếu reference; cần giữ tách biệt hai gói.

## Ledger mô phỏng

Schema `vi-pilot-simulation/0.1` có `kind=simulation`, roster, planned trial và attempts, snapshot/config fingerprint, seed, caps và reservation. SQLite `meta.plan_hash` đóng băng toàn bộ plan. Các bảng `trials`, `attempts`, `events` giữ thứ tự, trạng thái, request ID, lease, chi phí và sự kiện. Receipt giả có đúng `status`, `reward`, `inference_micros`, `compute_micros`.

`planned` được biểu diễn bằng trial chưa có attempt. Các phase còn lại là `reserved`, `submitted`, `completed`, `retryable_infra_error`, `verifier_error`, `agent_failure`, `uncertain`, `cancelled`. Uncertain có thể là chưa rõ kết quả hoặc đã biết reward nhưng chưa biết chi phí; xem [quy tắc runner](pilot-runner.md).
