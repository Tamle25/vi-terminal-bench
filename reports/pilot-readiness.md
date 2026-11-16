# Đánh giá sẵn sàng pilot

Ngày: 12/11/2026. **Chưa sẵn sàng chạy pilot model chính thức.** Mốc kỹ thuật native-six đã đạt; các phụ thuộc bên ngoài và hiệu chỉnh thực nghiệm còn thiếu.

Cập nhật tiếp nối: [stage3-readiness.md](stage3-readiness.md) ghi workaround relay command-only,4 smoke pass và41 test Linux. Bảng dưới giữ bối cảnh giai đoạn2; default WSL path chưa được sửa triệt để, model/review vẫn còn chờ.

| Điều kiện | Trạng thái | Bằng chứng hoặc việc tiếp theo |
|---|---|---|
| Sáu task B có EN/VI | Đạt kỹ thuật | Schema, expected tĩnh, oracle/controls và hash variants |
| Harbor và artifact Linux | Đạt kỹ thuật | 18 oracle pass, 6 nop fail, archive khôi phục được |
| Registry/preflight | Đã triển khai | Không hardcode hai task; filesystem probe và kiểm Compose offline |
| Adapter/coverage/bootstrap | Đã kiểm định theo profile development | 26 test; raw reference, manifest trước chạy và audit M1 |
| Review kỹ sư Việt Nam | Chờ | reports/reviews có hồ sơ pending; cần người khác tác giả |
| Hiệu chỉnh độ khó/thời gian | Chờ | Chưa đo thời gian chuyên gia hoặc model solve rate |
| Ổn định thời gian verifier | Cần điều tra | Hai outlier repeat 1; warm repeat bình thường, nguyên nhân chưa xác nhận |
| Docker CLI qua WSL cuối phiên | Chưa đạt | Probe timeout 30 giây dù Docker API Windows phản hồi; preflight fail-fast, cần xử lý trước run mới |
| Model/agent/ngân sách | Chưa có | Chọn hai cấu hình cụ thể, credentials, trần chi phí và giới hạn |
| Đường gọi API và agent setup | Chưa có | Agent ngoài sandbox hoặc image chuẩn bị sẵn/chính sách mạng phù hợp; verifier giữ offline |
| Task A và baseline | Chưa có | Snapshot/config/giấy phép theo checklist Eval |
| Quyền phát hành/split | Chờ chủ dự án | Chưa chọn license; hiện là development, chưa có private test |
| CI B đáng tin để xếp hạng | Chưa đủ dữ liệu | Mỗi skill chỉ có một family; công cụ trả null thay vì CI giả |

## Việc tiếp theo không cần baseline hoặc model có phí

1. Reviewer giải và review theo snapshot trong từng hồ sơ; sửa lỗi nếu có, tăng version và kiểm định lại phần ảnh hưởng.
2. Điều tra latency verifier, kiểm tra warm cache và tải runtime, phân biệt setup/transfer/grade trước lập ngân sách.
3. Hiệu chỉnh task, chuẩn bị dữ liệu test giữ kín theo family và mở rộng replication nếu cần CI theo nhóm.
4. Hoàn thiện model configuration/network profile rồi kiểm adapter với đúng profile đó; profile ngoài điều kiện default hiện tại phải được kiểm định thêm.

## Khi đã đủ đầu vào

- Có thể chạy B-only: 6 task × 2 instruction × 3 repeat × 2 cấu hình = **72 trial**, sau smoke test và review; công bố là native pilot.
- Pilot A+B đầy đủ: thêm 6 task A × 4 instruction × 3 repeat × 2 cấu hình = 144 trial, tổng **216**.
- Không gọi kết quả B-only là Terminal-Bench đầy đủ hoặc tự dùng baseline A không tương thích.
- Oracle/nop/control không được đưa vào điểm model. Các báo cáo development hiện tại không phải leaderboard.

Không phát sinh yêu cầu gửi dữ liệu ra ngoài hoặc công bố từ báo cáo này. Không có model run nào được thực hiện trong giai đoạn triển khai vừa qua.
