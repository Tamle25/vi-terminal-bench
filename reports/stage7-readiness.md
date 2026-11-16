# Readiness sau phần chuẩn bị giai đoạn 7

Đã thực hiện **U0 và phần chuẩn bị U1**: đối chiếu bằng chứng, kiểm tra đầu vào trong workspace và bàn giao [gói quyết định](stage7-decision-package.md). **G7.1 vẫn `missing_input`**, G7.2 chưa kiểm định, G7.3–G7.4 chưa chạy. Chưa có model/API call thật.

## Bằng chứng đã kiểm

- Snapshot sáu task/prompt, nguồn đã kiểm định, receipt chain/overlay và năm DB trong archive giai đoạn 6 vẫn đối chiếu được.
- Inventory mới bảo vệ hash 105 artifact/config/manifest đã có và 71 source file. Các template và manifest gốc giữ nguyên.
- 126/126 test Linux là bằng chứng kế thừa từ giai đoạn 6. Giai đoạn 7 chưa đổi executable nên không chạy lại bộ unit test hoặc integration fixture.
- Không có profile model, budget hoặc review accepted mới trong các cấu hình/hồ sơ đang dùng; reviewer của sáu task đều null/pending.

Đợt này thực hiện audit/kiểm tra read-only và validation dữ liệu cục bộ. Không xây thêm backend, simulation hay task, không đọc secret, chọn provider, probe Docker, nhập review hoặc gửi bundle/phát hành.

## Trạng thái cần giải quyết

| Điều kiện | Trạng thái hiện tại | Nơi tiếp tục |
|---|---|---|
| Reviewer và review record | `missing_input`, 0/6 | Chủ dự án giao reviewer, sau đó U2 |
| Hai cấu hình model/agent và giới hạn | `missing_input` | U1 → U3; dùng template hiện có |
| Budget/account/billing scope | `missing_input` | U1, sau đó nối tiền thực trong U3 |
| Runtime được chọn | `missing_input`, profile null | U1 → U4 |
| Binding/provider/isolation thực | `unverified` | U3–U4 sau khi có cấu hình |
| Manifest thực thi model | `unverified` | Đóng băng theo scope sau các quyết định/bằng chứng thật |
| Smoke 1–2 trial | Chưa chạy | U5 sau gate đạt và có scope/budget |
| Native pilot 72 trial | Chưa chạy | U6 sau smoke và review 6/6 |
| Phần A | `missing_input` | Checklist Eval; chưa nhập task A |

27 trường còn null gồm 12 trường cho mỗi cấu hình và ba budget cap. Gói quyết định phân biệt phần cần chủ dự án chọn với version/endpoint/mapping mà kỹ sư sẽ xác minh sau khi có agent/model/provider. Không cần tự điền toàn bộ thông số SDK khi chưa có lựa chọn nền tảng.

## Điểm kết thúc của đợt này

Theo [kế hoạch giai đoạn 7](../Plan/plan-giai-doan-7.md), khi đầu vào vẫn thiếu thì bàn giao inventory và gói quyết định, giữ trạng thái chưa chạy model. U1 chưa được đánh dấu đã chốt quyết định; U2–U7 tiếp tục mở. Các mốc model cũ cũng chưa hoàn tất.

Để tiếp tục, cung cấp các quyết định còn thiếu khi chúng sẵn có: reviewer, hai agent/model/provider, caps/account/pool, runtime/API architecture và yêu cầu prompt/tools/limits. Chỉ ghi tên cơ chế cấp credentials, không đưa giá trị secret vào repo/report. Những quyết định đã được cung cấp trong phiên tiếp tục có hiệu lực; không tạo vòng xác nhận trùng lặp.

Bằng chứng máy đọc: [inventory](stage7-input-state.json), [readiness model](stage7-model-readiness.json); tổng hợp tại `reports/stage7-summary.json`. Readiness/preview không phải token cho phép paid dispatch.
