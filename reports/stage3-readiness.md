# Trạng thái giai đoạn 3

Ngày12/11/2026. **Đã triển khai phần kỹ thuật không cần model; chưa hoàn thành pilot chính thức hoặc review độc lập.**

| Mục | Trạng thái |
|---|---|
| Q0 evidence | Hai archive cũ và sáu canonical payload giữ nguyên |
| Q1 chẩn đoán | Đã tái hiện lỗi ở default WSL socket; proxy Desktop trực tiếp hoạt động; chưa xác định nguyên nhân gián đoạn gốc |
| Q2 guard/process | Step-level preflight, timeout hữu hạn, owned process groups, executor job deadline; không hạ guard để chạy |
| Q3 smoke | 4/4 oracle pass, sequential, cached images/container sạch, archive restore đạt; chưa kiểm định concurrency2 hoặc dài hạn |
| Q4 review | Đã chuẩn bị public/reference bundle; tất cả hồ sơ vẫn pending |
| Q5 model dry-run | 72 planned trials,27 trường thiếu,6 task pending review;0 model calls, không executable |
| Q6 private test | Có ma trận family và quy trình; chưa viết private set hoặc chọn license |
| Q7/Q8 | Chưa chạy model, chưa có task A/baseline Eval |

[stage3-summary.json](stage3-summary.json) ghi bằng chứng kiểm tra/restore và bundle hashes. [stage3-unit-tests.json](stage3-unit-tests.json) có41 test Linux,0 fail/error/skip. Không dùng các con số control này làm model score.

## Runtime có điều kiện

[Scoped preflight](stage3-preflight-scoped-proxy.json) và3 health check qua relay đều đạt. Smoke mất khoảng31–43 giây/trial; pha verifier khoảng15–20 giây. Default path còn fail ở [preflight sau smoke](stage3-preflight-default-after.json), dù một probe trực tiếp trả nhanh. Không tuyên bố đã sửa triệt để socket hệ thống hoặc nguyên nhân outlier cũ.

Relay root chỉ tiếp cận socket Desktop được bảo vệ và phục vụ Unix socket0600 trong thời gian lệnh; benchmark command chạy bằng user thường. Không restart dịch vụ, không ghi Docker config, không TCP listener, không đưa Docker control socket vào agent/verifier. Các thư mục relay còn lại sau chạy được ghi trong summary; kết quả hiện tại là không còn thư mục.

**Điều kiện chạy mới:** default profile phải qua preflight hiện tại hoặc profile scoped relay phải được chọn rõ và kiểm định theo phạm vi tương ứng. Không tự bật quyền root cho model runner. Lỗi preflight vẫn chặn job và không biến thành model reward0.

## Quyết định còn cần đầu vào

- Reviewer thực sự giải và chấp nhận snapshot; bundles chỉ là gói chuẩn bị, không phải review đã xong.
- Hai agent/model, version/provider/endpoint/effort, prompt, budget và credentials mechanism.
- Chọn kiến trúc gọi API và kiểm định mapping/config/network thực tế; helper so profile dữ liệu thuần chưa thay được adapter agent-specific.
- Ngân sách smoke và72-trial pilot; không dùng thời gian oracle suy chi phí model.
- Nguồn phần A và quyết định license/phát hành/test kín.

Các kết quả và hạn chế chi tiết trong [runtime-diagnosis.md](runtime-diagnosis.md), [runtime-stability.md](runtime-stability.md), [model-pilot-dry-run.md](model-pilot-dry-run.md). Báo cáo giai đoạn2 giữ nguyên lịch sử; readiness hiện tại theo tài liệu này.
