# Recovery và accounting cho host agent

Ledger `vi-usd-ledger/1.1` dùng integer nano-USD; 1 USD = 1.000.000.000 nano-USD. Mỗi DB có account/cap/origin bất biến. `offline-fixture` không được đổi thành `real`. Version 1.1 từ chối mở DB identity/version khác trước DDL, không migrate archive fixture 1.0. Run giữ contract hash và cap inference/compute riêng; tổng exposure vẫn bị chặn ở pool chung.

Exposure request bằng giá trị lớn nhất giữa reservation và estimate khi chưa có invoice. Khi có invoice revision hợp lệ, dùng revision mới nhất làm charge, giữ nguyên raw/estimate. Không cộng các revision thành request mới. Chỉnh billing không tự xác định được outcome của một request uncertain. Compute có estimate riêng sau cleanup và invoice revision append-only riêng theo trial; khi chưa invoice giữ max(reserve, estimate). Quote/rate/authorization thực chưa có nên chưa dùng ledger này cho tiền thực. Phí build image là preparation riêng, chưa tự coi đã được quote của trial bao phủ.

Exposure connectivity được nhập bằng identity + evidence fingerprint, idempotent; thay receipt/reservation bị từ chối. Run cũ còn giữ 0,01 USD dù token estimate thấp hơn; không cộng cả hai thành 0,0100705 USD. DB và receipt giai đoạn 9 giữ nguyên. Cơ chế import có kiểm offline; pool thật chưa được tạo vì scope/caps/authorization smoke và compute pricing chưa chốt.

| Điểm ngắt | Trạng thái giữ | Xử lý |
|---|---|---|
| Trước claim trial | Chưa có trial | Đối chiếu gate/plan hiện tại; không dùng preview cũ làm quyền dispatch |
| Sau claim trial, trước request | Trial active, compute hold | Không tự claim lại; điều tra vì sao dừng trước khi quyết định phục hồi |
| Sau claim request, trước receipt | Request submitted, reserve giữ | Không gửi lại; chưa biết provider có nhận/tính phí hay không |
| Có receipt nhưng thiếu usage/outcome | Request uncertain | Chặn request tiếp; lưu bằng chứng và reconcile, không tự gán cost 0 |
| Có receipt/estimate đầy đủ | Observed; reserve vẫn giữ | Có thể đi tiếp trong cùng loop nếu gate/cap đạt; estimate chưa là invoice |
| Sau tool intent, trước result | Tool submitted | Không chạy lại command; nó có thể đã tạo/sửa file |
| Loop kết thúc | Raw stop record, reward null | Collect artifact, chạy trusted verifier, thêm normalized record riêng |
| Verifier/transfer lỗi | Reward null hoặc artifact thiếu | Phân loại infra; không biến thành model reward 0 |

Không có tự động resume partial trial. Không xóa DB, đổi trial ID để né claim hoặc replay từ đầu. Chưa có provider lookup/cancel, checkpoint recovery hoặc egress bảo đảm khi provider chậm; manual reconcile phải có evidence. Nếu operator cung cấp invoice, giữ source reference và revision; library hiện kiểm consistency/order, không xác thực hóa đơn từ provider.

Controller `terminal_smoke_v1.py` đã quản lý image identity, create/start, run loop, pause/transfer, verifier và cleanup; có kiểm lifecycle fixture. Shared ledger path nằm trong approved config và ở storage Linux bền vững, không nằm trong output directory hoặc `/tmp`; đổi state folder không reset claim/run budget. Controller không tiếp tục trial hai khi trial trước không hợp lệ, cleanup fail hoặc có uncertainty. Container TTL và bound verifier được dùng để tính compute reservation tối thiểu từ quote; estimate và invoice vẫn khác nhau.

Container integration chưa kiểm do Docker/WSL không đạt. Khi runtime hoạt động cần kiểm image preparation, lifecycle/timeout/cleanup thật, worker HTTP và nguồn compute quote trước smoke. Capture attestation ngay trước trial, không dùng report chẩn đoán lỗi làm attestation.
