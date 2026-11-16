# Readiness sau giai đoạn 5

Đã đạt **G5.1–G5.2 trong phạm vi offline**: hợp đồng scope/adapter, mẫu review gắn hash, orchestration gọi gate trước request và ledger hai cấp attempt/request. **G5.3–G5.5 chưa đạt** do thiếu review, cấu hình và kiểm định thực. Các mục G4.3–G4.5 vẫn mở.

102/102 test Linux/WSL đạt, không skip. Integration CLI mới hoàn tất hai trial fixture qua ba attempt/năm request, resume qua ba tiến trình và khôi phục archive đều khớp. Không gọi model/API thật, đọc secret, probe Docker, gửi bundle hoặc publish. Xem [kiểm định executor](model-executor-offline-validation.md).

## Trạng thái trước model run

[Readiness JSON hiện tại](stage5-model-readiness-current.json) trả `ready_for_dispatch=false`, `ready_for_model_dispatch=false`, `authorization_token=false`. `--mode model` chỉ validate; chưa có binding provider thực để dispatch.

| Điều kiện | Trạng thái | Đầu vào/công việc tiếp theo |
|---|---|---|
| Hai cấu hình agent/model và budget | `missing_input` | Chủ dự án cung cấp 27 trường còn thiếu theo template và giới hạn smoke/pilot |
| Review độc lập | `missing_input`, 0/6 | Chỉ định kỹ sư Việt Nam khác tác giả; giải/review và cung cấp record thực đúng hash |
| Runtime vận hành model | `unverified` | Chọn profile, kiểm CLI/engine/isolation/cleanup thực và capture mới theo run |
| Effective adapter | `unverified` | Chọn agent/version, mapping/kwargs/tools/API architecture thực; fixture không thay bằng chứng này |
| Provider binding, usage/pricing | `unverified` | Triển khai binding của provider đã chọn, nguồn giá hiện hành và cơ chế theo dõi phí từng request |
| Manifest model | `unverified` | Hiện mới có preview tự sinh; cần đóng băng manifest thực sau các quyết định |
| Phần A | `missing_input` | Snapshot/config/quyền dùng từ Eval vẫn chưa có |
| Private set và phát hành | Chưa thực hiện | Nhánh riêng sau pilot và quyết định của chủ dự án |

Không hỏi lại các đầu vào người dùng đã xác nhận chưa có. Đã chuẩn bị phần có thể thực hiện độc lập; các trường thiếu không được điền bằng model, reviewer hay số tiền tùy chọn.

## Sản phẩm bàn giao

- [Inventory đầu vào](stage5-input-state.json) lưu hash các report/archive stage4 để phát hiện thay đổi.
- [Mẫu review chưa điền](../configs/review-records.stage5.template.json) chứa hash và attribution hiện tại, không phải accepted record. Người review thực hoàn tất từng record và xuất JSON array theo [schema](../docs/pilot-state-schema.md).
- [Hợp đồng executor](../docs/model-executor-contract.md) và [CLI](../docs/model-executor.md) phân biệt scope, origin, source provenance, reservation và receipt.
- [Bằng chứng offline](stage5-offline-summary.json) lưu nền tảng, chi phí giả, hash source và archive; tổng hợp tại `reports/stage5-summary.json`.

Runtime default WSL còn lịch sử gián đoạn; relay stage3 chỉ là workaround development. Giai đoạn này kiểm filesystem Linux trong test và các fixture runtime, không thu attestation Docker/model thực hoặc chọn profile thay người vận hành. Policy network trong JSON vẫn cần enforcement/kiểm định agent thật.

## Thứ tự tiếp tục khi có đầu vào

1. Giao review public trước reference, đo thời gian giải và nhập accepted đúng snapshot. Task lỗi phải version hóa/kiểm định lại phần bị ảnh hưởng.
2. Điền hai profile và chọn runtime, kiến trúc gọi API cùng caps smoke/pilot. Không lưu giá trị credentials trong repo hoặc report.
3. Triển khai provider binding theo agent đã chọn; kiểm effective config, isolation/cleanup, nguồn giá/usage, accounting và recovery khi partial/uncertain. Nếu chung provider account/budget, kiểm tổng exposure giữa smoke và pilot.
4. Gate đạt cho scope tương ứng mới chạy smoke 1–2 trial. Smoke kiểm đường thực thi/accounting, không cần chọn lại task cho tới khi model pass.
5. Sau smoke đạt, chạy 72 trial B thật trong budget đã có; giữ mọi attempt/cost và báo coverage thực. Một family/skill vẫn chưa đủ CI B; không lấy best-of-three.

Toàn bộ việc còn mở được giữ trong [kế hoạch giai đoạn 5](../Plan/plan-giai-doan-5.md). Không cần tăng số task hoặc tạo thêm simulation để thay thế reviewer và cấu hình thực.
