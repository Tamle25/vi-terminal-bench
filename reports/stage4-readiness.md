# Readiness sau giai đoạn 4

Đã hoàn thành phạm vi offline **G4.1–G4.2**: hợp đồng trạng thái/runtime/review, readiness gate, runner mô phỏng có ledger/retry/resume và kiểm định 72 trial. **Chưa sẵn sàng dispatch model; G4.3–G4.5 chưa hoàn tất.**

70/70 test Linux/WSL đạt, không skip. Mô phỏng có 72 kết quả cuối, 74 fake dispatch, hai retry giữ đầy đủ phí; dừng/resume qua ba tiến trình và phục hồi archive đều khớp. Không đọc API key, gọi model, gửi gói review hoặc phát hành dataset. Xem [báo cáo runner](pilot-runner-offline-validation.md).

[Tổng hợp máy đọc](stage4-summary.json) ghi kết quả kiểm tra bàn giao: hash lịch sử, liên kết raw, tổng phí giả lập, namespace, UTF-8, AST, JSON và các liên kết tài liệu đều đạt.

| Điều kiện | Trạng thái hiện tại | Công việc tiếp theo |
|---|---|---|
| Model profile | `missing_input`: 27 trường chưa có trong template | Chủ dự án cung cấp hai agent/model cụ thể, giới hạn và kiến trúc API |
| Review độc lập | `missing_input`: 0/6 accepted | Chỉ định reviewer người Việt khác tác giả; cung cấp record gắn đúng hash |
| Runtime model | `missing_input`: chưa chọn profile | Chọn native hoặc scoped relay; capture mới theo run và scope |
| Adapter hiệu lực | `unverified` | Triển khai và kiểm định mapping/isolation với agent thật được chọn |
| Ngân sách | `missing_input` | Trần smoke/pilot, giá hiện hành, reservation và ledger thực |
| Execution manifest | `unverified` | Đóng băng manifest model sau các quyết định trên; preview không thực thi được |

[JSON gate](stage4-model-readiness.json) trả `ready_for_dispatch=false`, `authorization_token=false`, `model_calls=0`. Gate chỉ kiểm tra sự nhất quán bằng chứng; chưa có executor model thật để nối vào gate. `--mode model` của runner mô phỏng luôn từ chối.

## Bằng chứng được bảo toàn

[Inventory đầu vào](stage4-input-state.json) đối chiếu đủ năm archive cũ: M1, native-six, stage3 smoke và hai gói review public/reference. Canonical snapshot sáu task/prompt giữ nguyên; không áp dụng record review giả, không tăng version hoặc viết lại báo cáo giai đoạn trước. Task vẫn do Codex hỗ trợ soạn, độ khó provisional.

Default WSL socket có lịch sử lỗi gián đoạn; stage3 scoped relay đã đạt smoke development, không phải sửa triệt để default integration. Giai đoạn này không probe lại Docker hoặc bật relay/root cho model. Profile/capture mới chỉ được kiểm bằng unit fixture; runtime attestation thật và cleanup cho model run chưa có. Policy network/socket trong JSON vẫn cần adapter enforcement thực tế.

## Bàn giao và thứ tự tiếp tục

1. Review theo [hướng dẫn](../docs/review-guide.md), mở public trước, giữ reference riêng; nhập record bằng [schema](../docs/pilot-state-schema.md). Không tự accepted từ oracle pass.
2. Điền [template cấu hình](../configs/model-pilot.template.json) bằng quyết định thực của chủ dự án và chọn runtime trong [danh mục](../configs/runtime-profiles.json). Không lưu giá trị secret vào repo.
3. Thực hiện [mapping agent](../docs/model-profile-mapping.md), kiểm định API/isolation/cost và triển khai executor thật. Capture runtime mới theo run, kiểm tra gate ngay trước dispatch.
4. Smoke 1–2 trial với budget riêng; đạt mới chạy 72 trial B thật, giữ mọi attempt và phí, không lấy best-of-three.

Phần A vẫn thiếu snapshot/config Eval; private set và phát hành chưa triển khai. Không tạo report điểm model giả để thay các đầu vào còn thiếu. Các bước offline có thể tái lập theo [hướng dẫn runner](../docs/pilot-runner.md); toàn bộ kế hoạch tiếp tục ở [giai đoạn 4](../Plan/plan-giai-doan-4.md).
