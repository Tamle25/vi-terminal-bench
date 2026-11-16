# Thông tin cần từ đội Eval trước phần A

Chưa có theo xác nhận của người dùng ngày 12/11/2026. Đây là checklist nội bộ, chưa gửi thông tin ra ngoài.

- Dataset ref/commit và danh sách task, hash task/instruction/verifier.
- Bản 4.0 hay verifier đã cập nhật; có artifact để chấm lại không.
- Giấy phép, NOTICE và phụ thuộc từng task, tài nguyên GPU/multi-container.
- Model ID/version, provider, agent/version, system prompt và tool configuration.
- Harbor/version, image digest, timeout, token/turn/effort, CPU/RAM và mạng.
- Số repeat, thứ tự chạy, seed nếu có, ngày chạy.
- Reward từng trial, lỗi, retry, trajectory, token/chi phí nếu có.

Chỉ dùng baseline cũ khi điều kiện trọng yếu khớp; nếu không, chạy lại EN cùng snapshot với VI. Sáu task A của pilot phải được chọn sau kiểm tra tài nguyên, không tự gọi subset là toàn bộ Terminal-Bench.
