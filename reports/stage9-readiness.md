# Readiness sau giai đoạn 9

Cập nhật 13/11/2026: đã vượt bước chỉ kiểm offline. **Một request OpenAI thực thành công**, chi phí token ước tính 0,0000705 USD trong trần 2 USD; **164/164 test Linux** đạt, không skip. Xem [kết quả kết nối](provider-connectivity.md) và [summary máy đọc](stage9-summary.json).

| Mốc / scope | Trạng thái | Căn cứ hoặc phần còn thiếu |
|---|---|---|
| G9.1 — Run spec kết nối | Đạt trong scope này | Người dùng ủy quyền chọn model và trần 2 USD; cấu hình đóng băng, nguồn credential cục bộ xác định; project ID của provider chưa xác minh |
| G9.2 — Kết nối provider | Đạt | HTTP 200, completed, đúng snapshot model, request ID/usage/ước tính chi phí thực |
| Accounting connectivity | Có token estimate; chờ invoice | Ledger USD riêng, reservation 0,01 USD còn giữ; không tích hợp shared USD pool nhiều run |
| G9.3 — Terminal benchmark smoke | Chưa chạy | Cần reviewer độc lập cho task được chọn, agent terminal/version/tools và runtime attestation; cap cho scope smoke |
| G9.4 — Pilot 72 trial | Chưa chạy | Sau smoke: review 6/6, hai cấu hình so sánh, budget pilot và shared accounting thực |
| Phần A | Thiếu đầu vào | Chưa có snapshot/cấu hình baseline từ Eval |
| Phát hành dataset | Chưa thực hiện | Development sáu task; chưa review độc lập |

Nguồn task, prompt, attribution, artifact lịch sử và giấy phép không đổi. 295 đường dẫn trong evidence lịch sử được đối chiếu hash; snapshot task/prompt giữ nguyên. Bộ test giai đoạn 9 chạy bằng Python 3.12.16 trên bản sao filesystem Linux có kiểm bytes, gồm 14 test mới cho cap, claim/replay, drift, transport và redaction. Native snapshot có 194 input công khai, không chứa `.env`. Không chạy lại integration fixture lớn hoặc tạo điểm model giả.

Bước tiếp theo có giá trị là **review độc lập một task B rồi nối agent terminal cho một smoke có budget riêng**. Dùng [review guide](../docs/review-guide.md) và [review template](../configs/review-records.stage5.template.json), ghi reviewer/thời gian/phiên bản và payload hash thực; AI tự kiểm không thay reviewer độc lập. Agent cần command execution, artifact transfer, trajectory và request accounting; container không được thấy oracle/test kín/key hoặc Docker control socket. Kiểm runtime với concurrency 1 và capture attestation mới trước trial.

Không cần kiểm lại key bằng một request connectivity khác. Run hiện đã dùng một attempt duy nhất; không xóa DB để resend. Trần 2 USD hiện được chốt cho đợt kiểm tra, chưa tự chuyển thành ngân sách pilot. Phần 2 USD chưa dùng không có nghĩa là đã cấp thêm scope hoặc xác minh số dư tài khoản.

Các mốc lịch sử G8.2–G8.5 giữ ý nghĩa ban đầu: đã có client kết nối text nhưng chưa có binding terminal agent/accounting nhiều request cho smoke. G7.1 nay đã giải quyết một phần model/cap kết nối, còn reviewer, hai profile pilot, runtime và các ngân sách tương ứng. Giai đoạn 9 **hoàn thành W0–W3 trong scope connectivity; W4–W6 còn mở**.
