# Dashboard benchmark cục bộ

Tại root dự án, chạy bằng Python 3.11 trở lên:

```powershell
python dashboard/server.py
```

Mở **http://127.0.0.1:8765**. Hoặc chạy `powershell -ExecutionPolicy Bypass -File dashboard/start-dashboard.ps1`. Server không cần cài thư viện Python/npm. Để đổi cổng: `python dashboard/server.py --port 8766`.

Trang mở kết quả baseline đã nghiệm thu: 35/36 lượt đạt. Bạn có thể lọc tiếng Anh/Việt, tìm tác vụ có dấu hoặc không dấu, xem artifact và tải CSV UTF-8 BOM/JSON. Các lần chạy mới được ghi riêng trong lịch sử.

Trên điện thoại, bảng giữ tên tác vụ, ngôn ngữ và kết quả; bấm mũi tên của từng dòng để xem repeat, thời gian, token, chi phí và artifact. Bộ lọc cũng được lưu trên URL để bạn có thể mở lại.

Luồng thử đề nghị:

1. Vào **Chạy benchmark → Xem trước kế hoạch**. Lệnh này chỉ đọc manifest/config, không cần Docker/WSL, không đọc key và không gọi API.
2. Mở Docker Desktop; tại dashboard bấm **Kiểm backend**. Backend dùng profile WSL/relay đã kiểm của dự án; tái sử dụng validation còn khớp source, kiểm các image vẫn tồn tại hoặc build/kiểm oracle + no-op khi cần.
3. Bấm **Đồng bộ ngân sách** để đọc ledger hiện tại mà không gọi model.
4. Chọn **Smoke test → Chạy smoke · 2 lượt**. Thao tác này gọi OpenAI thật bằng key `.env` hiện có, chạy B001 EN/VI và tự chấm artifact. Không cần nhập key trên trình duyệt.
5. Sau smoke, có thể chọn **Benchmark đầy đủ → Chạy batch · 36 lượt**. Batch cần smoke hợp lệ cùng source/config; chương trình dùng evidence thật và ledger để kiểm điều kiện.

Giới hạn model/request/time và pool **2 USD dùng chung** giữ nguyên theo CLI. Không có ô sửa model hoặc tăng ngân sách. Chi phí trên thẻ tổng quan thuộc đúng lần chạy được chọn; exposure ngân sách gồm cả dự phòng, khác với phí token. Ngân sách hiển thị theo snapshot hoặc ledger gần nhất có ghi rõ nguồn; CLI vẫn kiểm lại trước mỗi request. Compute local chưa đo phí, estimate token chưa phải invoice.

Tác vụ model cần WSL `Ubuntu-22.04`, user `tamle`, Python `/home/tamle/vi-terminal-bench-stage11/venv/bin/python` và Docker Desktop đang chạy. Máy khác cần thiết lập runtime theo [quickstart](../docs/development-benchmark-quickstart.md). Dashboard không tự cài Docker hoặc thay cấu hình benchmark đã khóa. Không khởi chạy CLI khác song song với dashboard.

Đóng tab không dừng job khi server vẫn chạy. Giữ terminal/server hoạt động đến khi hoàn tất; không dùng Ctrl+C giữa lúc gọi model. Nếu server bị ngắt, lịch sử chuyển sang “Cần kiểm tra”; không tự gửi lại. Nút **Tiếp tục phần chưa gửi** chỉ gọi `resume-unstarted` của CLI, giữ nguyên run ID, outcomes và ledger. Partial/unknown vẫn bị từ chối; dashboard không gọi công cụ reconcile hoặc xóa state. Lỗi agent reward 0 được giữ nguyên.

Job/log/export giao diện nằm trong `.dashboard/` (được Git ignore); evidence thực và ledger tiếp tục nằm ở filesystem Linux theo config. **Dựng lại baseline** đọc ledger/outcome thật để xuất một report mới, không gọi API. File baseline gốc, source freeze và báo cáo giai đoạn 11 không bị ghi đè.

Chế độ QA: `python dashboard/server.py --read-only` chặn smoke/batch/resume ở backend và lưu lịch sử riêng tại `.dashboard/qa/`. Chế độ thường lưu tại `.dashboard/runtime/`; cả hai vẫn đọc cùng ledger benchmark, không tạo pool mới. Không dùng chế độ QA khi bạn muốn bấm chạy model thật.

Dashboard dùng adapter đồng hồ `dashboard-boottime-utc-v1` cho capture và kiểm tra runtime: neo UTC một lần vào `CLOCK_BOOTTIME` trong cùng tiến trình, tính cả thời gian máy suspend. Điều này tránh bước lùi của wall clock WSL làm attestation vừa cấp bị coi là “ở tương lai”. Validator gốc vẫn kiểm đủ identity, snapshot, network và hạn 900 giây; không cộng tolerance hay kéo dài hạn. Không chỉnh giờ hệ thống. Bản sửa áp dụng cho đường chạy dashboard, CLI cũ vẫn giữ nguyên source freeze.

Mỗi lần chạy/tiếp tục có receipt và ZIP source adapter tại `<state_root>/runtime-revisions/<run-id>/`; attestation cũng lưu clock policy và giờ hệ thống quan sát riêng. Đây là revision runtime được ghi rõ, không gắn nhãn toàn bộ controller giống hệt bản baseline cũ.

Khi tiếp tục, chỉ lỗi attestation **trước vòng model**, chưa có request/tool intent hoặc trajectory, mới được backup và archive bằng `dashboard/recovery.py`. Evidence lỗi gốc vẫn giữ trong `blocked-trials/`, raw outcome và mọi khoản phí giữ nguyên. Có request đã gửi, timeout/unknown, hoặc tool intent thì không đủ điều kiện phục hồi này. Xem [chẩn đoán lần lỗi thực tế](../reports/dashboard-attestation-diagnosis.json) và [kiểm gate sau sửa](../reports/dashboard-resume-preflight.json).

Server chỉ bind loopback, khóa một instance, chỉ phục vụ allowlist static/download; không có endpoint đọc `.env`, chạy shell tùy ý hoặc truyền key lên trình duyệt. Lệnh POST cần đúng Host/Origin và session token. Không dùng dashboard này như dịch vụ mở Internet.

Kiểm thử riêng của dashboard:

```powershell
python -m unittest discover -s dashboard/tests -v
node --check dashboard/static/app.js
```
