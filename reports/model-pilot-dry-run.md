# Dry-run native model pilot

Đã chạy [template](../configs/model-pilot.template.json) qua công cụ offline. [JSON preview](stage3-model-dry-run.json) có72 planned trial ID duy nhất: 6 task × EN/VI × 3 repeat × 2 cấu hình. Có payload/instruction/config fingerprints, expected configurations và attempt→job routing.

**Không thực thi được:** kind=offline-dry-run-not-executable, model_calls=0, secrets_read=false. Có27 trường đầu vào còn thiếu và6 task review pending. Runtime/agent-specific adapter chưa được xác minh cho model thật. Không có paid smoke, model result hoặc leaderboard.

Thiếu: agent/version/model/provider/endpoint/effort/prompt, token/turn/time, kiến trúc, tên biến credentials và các trần tiền. Không tự chọn hoặc điền các giá trị này thay người phụ trách. `ready_for_model_calls=false` không bị đổi chỉ vì lịch chạy đã đủ72 dòng.

[Hướng dẫn profile](../docs/model-run-profile.md) mô tả cách điền an toàn và phần mapping thực tế còn phải làm. Runner oracle/nop giữ guard cũ, không nhận preview này để chạy model. Nếu cần phê duyệt model/ngân sách sau này, trình preview cụ thể cùng cấu hình đầy đủ trước; hiện chưa có yêu cầu quyết định hay gửi dữ liệu ra ngoài.
