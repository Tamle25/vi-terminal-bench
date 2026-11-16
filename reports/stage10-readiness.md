# Readiness sau triển khai giai đoạn 10

Cập nhật 13/11/2026: đã thêm host agent/tool loop, controller lifecycle, worker HTTP có deadline, Docker/artifact/verifier primitive, ledger USD nhiều request/compute revision và gói review pending. **203/203 test Linux đạt**, cùng integration fixture EN/VI. **Không có API request mới hoặc benchmark smoke thật.**

| Mốc | Trạng thái | Bằng chứng / phần còn thiếu |
|---|---|---|
| G10.1 — Thiết kế và hồ sơ | Đạt cho thiết kế/draft | Inventory kiểm 309 đường dẫn lịch sử; source, config, run spec và kit B001 đã có; thiếu đầu vào ghi rõ |
| G10.2 — Agent/accounting | Implementation đã kiểm offline; backend thực chưa nghiệm thu | Loop/ledger/controller/worker/compute revision đã kiểm; container integration, quote và real tool/usage mapping vẫn chưa xác minh thực |
| G10.3 — Sẵn sàng smoke | Chưa đạt | Review B001 pending, Docker/WSL fail, runtime/caps/authorization/compute chưa chốt, chưa có attestation mới |
| G10.4 — Smoke có kết quả | Chưa chạy | Hai trial mới planned; reward model chưa có |
| Pilot B / phần A / phát hành | Chưa chuyển mốc | Pilot cần review 6/6, hai cấu hình và budget; A cần snapshot Eval; license task chờ chủ dự án |

Đã kiểm ledger connectivity read-only, một run `observed`, exposure 0,01 USD vẫn giữ; token estimate 0,0000705 USD chưa invoice. Không đọc key thật hoặc release reservation. Tài liệu trạng thái giai đoạn 9 được đối chiếu trong archive gốc; README/kế hoạch tổng thể có thể cập nhật mà không sửa summary lịch sử.

Lựa chọn triển khai: stdlib host loop độc lập executor fixture; model snapshot đã kết nối, schema smoke một profile, tool terminal strict. Giảm draft từ tám xuống **bốn request/trial** để dự phòng toàn bộ maximum input model, tối đa 1,668864 USD inference cho tám request. Đây là bound/đề xuất review được, chưa phải ngân sách đã cấp hoặc khoản chi mới. Xem [run spec](stage10-run-spec.md).

Người dùng xác nhận chưa có người review, nên [kit B001](reviews/stage10-b001-opening.zip) giữ pending. Kit có hai instruction, CSV đúng byte/hash gốc và template; không gồm đáp án. Không liên hệ reviewer thay người dùng và không tự ghi human acceptance. Acceptance hiện vẫn 0/6.

Việc cần làm tiếp theo:

1. Người vận hành khôi phục Docker Desktop WSL integration trong profile đã chọn; chạy lại chẩn đoán/preflight và kiểm lifecycle container bằng fixture trước khi mở model.
2. Kiểm controller create/start → loop → pause/transfer → separate verifier → cleanup, hard deadline/egress và compute quote bằng backend thực. CLI execute đã có precheck, draft hiện không được dispatch.
3. Giao B001 cho kỹ sư Việt Nam khác tác giả, thu record và thời gian thực đúng snapshot. Chuẩn bị phần kỹ thuật không cần chờ người review.
4. Chốt scope/caps/compute cho smoke bằng cấu hình đã có thể review; tái sử dụng quyền đã cấp nếu áp dụng đúng scope, không mặc định trần connectivity là budget pilot.
5. Khi tất cả gate đạt, đóng băng approved run và attestation mới, chạy đúng EN/VI đã lập trước rồi lưu request/usage/reward/billing. Reward 0 do giải sai vẫn có thể là quan sát hợp lệ.

Không chạy pilot 72 trial hoặc mở rộng task trong giai đoạn này. [Summary máy đọc](stage10-summary.json), [kiểm định offline](terminal-agent-offline-validation.md), [thiết kế](../docs/terminal-agent-design.md) và [recovery](../docs/terminal-agent-recovery.md) ghi giới hạn tương ứng. [Kiểm CLI draft](stage10-dispatch-guard.json) ghi nhận execute bị từ chối trước Docker/key, không phát sinh request và ledger cũ không đổi. Giai đoạn 10 là **bàn giao kỹ thuật một phần**, không được ghi hoàn thành toàn giai đoạn hoặc smoke pass.
