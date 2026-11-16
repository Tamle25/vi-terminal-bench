# Kiểm kết nối OpenAI có giới hạn

Đường triển khai này dành riêng cho run đã chốt ở [run spec](../reports/stage9-run-spec.md). Không nối vào executor benchmark cũ hoặc sửa guard của ledger mô phỏng. Registry trong code chỉ hỗ trợ OpenAI Responses, model/prompt/limits cố định; endpoint không nhận từ biến môi trường. Binding chưa hỗ trợ terminal tools, streaming, retry, checkpoint lookup, cancel hoặc tự reconcile invoice.

```powershell
# Chỉ preview, không đọc credential hoặc gọi API.
python scripts/provider_connectivity_v1.py
# Kiểm input công khai và đóng băng một lần; từ chối ghi đè evidence.
python scripts/stage9_prepare.py
# Chỉ dùng khi run chưa có claim và vẫn có authorization/budget hợp lệ.
python scripts/provider_connectivity_v1.py --execute
# Chỉ khôi phục artifact từ receipt đã lưu, không gửi lại request.
python scripts/provider_connectivity_v1.py --export
```

Run stage9 chỉ được gửi một lần. Khi evidence/claim đã tồn tại, không chạy lại chuỗi lệnh như hướng dẫn reset. Một run khác cần manifest/authorization/accounting mới và phải tính exposure còn giữ của run cũ vào ngân sách chung; script hiện tại cố ý không cung cấp chức năng mở run tiếp theo.

Trong `jobs/stage9-connectivity/ledger.sqlite3`, bảng `runs` giữ manifest, reservation, state và receipt. `reserved` hoặc `submitted` sau crash đều ngăn resend. Receipt công khai trong `reports/provider-connectivity-stage9.json` giữ request ID, model, usage, lỗi đã redaction và cost estimate; trạng thái HTTP không đủ chứng minh tính phí hoặc quota cho lần sau. Nếu có correction/hóa đơn, tạo evidence revision mới tham chiếu receipt gốc; không sửa lịch sử hoặc cộng mỗi revision thành request riêng.

Giá trị key chỉ đi từ scoped loader tới HTTPS client trong process. Raw request Authorization, dotenv và môi trường process không được xuất ra artifact. Source archive dùng danh sách public rõ ràng; không archive nguyên workspace. Test dùng credential fixture trong thư mục tạm, không đọc key thật.
