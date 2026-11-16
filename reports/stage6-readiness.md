# Readiness sau giai đoạn 6

Đã đạt **G6.1–G6.2 trong phạm vi offline**: ledger ngân sách chung theo pool/run, outbox giữa hai DB, receipt revision, CLI quan sát/import/replay và billing overlay. **G6.3–G6.4 chưa đạt**; G4.3–G4.5 và G5.3–G5.5 tiếp tục mở.

126/126 test Linux đạt, không skip. Integration hai request fixture/bốn receipt revision kiểm unknown smoke chặn pilot, reservation theo số dư pool, crash/replay và điều chỉnh phí; năm DB restore khớp. **0 model/API call thật**, không đọc secret hoặc probe Docker. Xem [báo cáo kiểm định](shared-billing-offline-validation.md).

## Điều kiện còn thiếu

| Điều kiện | Trạng thái | Hành động tiếp theo |
|---|---|---|
| Reviewer độc lập | `missing_input`, 0/6 accepted | Chủ dự án giao kỹ sư Việt Nam khác tác giả, giải/review theo hash và nhập record thực |
| Hai agent/model/version và prompt/tools | `missing_input` | Điền quyết định thực theo template hiện có; 27 trường cấu hình/budget còn thiếu |
| Budget và billing scope/account thực | `missing_input` | Chốt caps smoke/pilot/pool, account reference và currency; không lấy cap SIM_USD làm ngân sách thật |
| Provider binding/pricing/usage | `unverified` | Triển khai đúng adapter được chọn; xác minh giá, request IDs, SDK retry và receipt nguồn thực |
| Runtime và API isolation | `unverified` | Chọn profile, kiểm engine/user/endpoint/egress/resource/cleanup và capture mới theo run |
| Recovery provider/checkpoint | `unverified` | Kiểm lookup/cancel/billing và checkpoint theo capability; partial thiếu bằng chứng vẫn giữ uncertain |
| Manifest model thực | `unverified` | Chưa có manifest đóng băng theo các quyết định thật; bản tự sinh là preview |
| Phần A | `missing_input` | Snapshot/config/quyền dùng từ Eval vẫn chưa có |
| Private set/phát hành | Chưa thực hiện | Nhánh có điều kiện riêng sau pilot và quyết định của chủ dự án |

[Readiness model JSON](stage6-model-readiness.json) vẫn trả false cho dispatch/model dispatch. Core model guard được giữ nguyên; các class billing mới chỉ nối adapter fixture và từ chối pool USD. Không có registry provider thực hoặc secret loader.

## Bàn giao

- [Inventory đầu vào](stage6-input-state.json): snapshot và hash report/archive giai đoạn 5 được bảo toàn.
- [Ledger contract](../docs/shared-billing-ledger.md): run/pool caps, uncertainty, outbox và authoritative billing overlay.
- [Runbook](../docs/reconciliation-runbook.md): status read-only, receipt import/replay và giới hạn recovery.
- [Test bản cuối](stage6-final-unit-tests.json), [integration](stage6-final-offline-summary.json), tổng hợp tại `reports/stage6-summary.json`.

Billing account reference trong fixture chỉ là nhãn test, không phải account chủ dự án đã chọn. Nguồn receipt và raw hash hiện kiểm tính nhất quán; xác minh provider-issued evidence thuộc binding thực tương lai. Event append-only là quy tắc của code, không phải bảo đảm chống sửa DB bằng quyền ngoài ứng dụng.

Legacy task fee được bảo toàn khi billing correction; tổng tài chính mới phải lấy từ ledger/overlay kèm delta. Partial nhiều request chưa có checkpoint không được tự tiếp tục, resend hoặc gán reward mới. Reconciliation cập nhật dữ liệu phí/kết quả có bằng chứng, không thay gate trước request mới.

Runtime default WSL còn lịch sử gián đoạn, relay stage3 chỉ được kiểm development. Giai đoạn này dùng native Linux cho test/ledger nhưng chưa chọn hoặc kiểm lại runtime Docker/model thực. Không thay socket, restart dịch vụ, gửi bundle hoặc publish dữ liệu.

## Thứ tự tiếp tục

1. Hoàn tất review và hai cấu hình cùng phạm vi budget/account thực; dùng lại [template model](../configs/model-pilot.template.json) và [template review](../configs/review-records.stage5.template.json).
2. Triển khai provider binding theo source/tài liệu chính thức của đúng agent/version; kiểm effective config, pricing/usage, SDK retries, nguồn receipt và recovery capability.
3. Kiểm runtime/isolation/cleanup, thu attestation mới và đóng băng manifest thực. Giữ tài chính chung smoke/pilot trong pool được chủ dự án chọn.
4. Gate đạt theo scope mới chạy smoke 1–2 trial; sau smoke đạt và billing đã rõ, chạy pilot B 72 trial trong budget đã có. Giữ mọi retry/cost, báo coverage thiếu và CI null khi không đủ family replication.

Không cần thêm task hoặc một bộ 72 trial giả lập để thay đầu vào thực còn thiếu. Checklist tiếp tục ở [kế hoạch giai đoạn 6](../Plan/plan-giai-doan-6.md).
