# Readiness sau phần triển khai offline giai đoạn 8

Cập nhật 13/11/2026. Đã hoàn thành V0 và phần credential loader/redaction/source-policy độc lập của V2. **150/150 test Linux đạt**, không skip. Key thật giữ nguyên trong `.env`; đợt triển khai chỉ kiểm metadata của file, không đọc giá trị key hoặc gọi API.

**G8.1 đạt cho credential storage; G8.2 mới đạt phần loader offline, chưa hoàn tất binding/config.** G8.3 unverified, G8.4–G8.5 chưa chạy. G7.1 và các mốc model trước đó vẫn chưa hoàn tất.

## Phần đã có

- Loader tường minh, environment ưu tiên, không sửa `os.environ` toàn cục; chỉ cấp cho target host-agent/model-api-client sau gate callback.
- Lease đóng khi thoát context; metadata và error có output giới hạn, hỗ trợ structured redaction.
- Source policy loại `.env` khỏi native test snapshot, từ chối private dotenv/symlink/outside path và kiểm example rỗng.
- `.env.example` không có secret; metadata CLI không đọc key thật.
- Regression gồm 126 test trước đó và 24 test mới. Không có thêm một run 72 trial simulation hoặc model run.

Xem [báo cáo kiểm định](credential-loader-validation.md) và [hướng dẫn loader](../docs/credential-loading.md).

## Điều kiện còn thiếu

| Điều kiện | Trạng thái | Hành động tiếp theo |
|---|---|---|
| Key hợp lệ/quyền model/quota | `unverified` | Kiểm qua đường chạy thực có scope/budget khi cấu hình đã có |
| Hai agent/model/provider và giới hạn | `missing_input` | Chốt cấu hình theo template; không suy model từ key đã lưu |
| Budget/account/pool tiền thực | `missing_input` | Chốt caps/scope/currency/account reference và nguồn giá hiện hành |
| Provider SDK/agent binding | `unverified` | Chọn agent, triển khai mapping/effective config/request/usage/SDK retry và client factory |
| Runtime/isolation/attestation | `unverified` | Chọn profile và kiểm thực theo run trước dispatch |
| Review task | `missing_input`, 0/6 | Reviewer người Việt độc lập hoàn tất record đúng hash |
| Smoke/pilot | Chưa chạy | Gate đạt theo scope mới chạy smoke, sau đó pilot 72 trial |
| Phần A/private/release | Chưa thực hiện | Theo đầu vào Eval, thiết kế sau pilot và quyết định riêng |

Template còn 27 field null. Tên biến `OPENAI_API_KEY` đã biết và có thể dùng cho profile OpenAI được chọn, nhưng chưa tự điền cả hai cấu hình hoặc mặc định provider/account của chúng. Credential file hiện diện không tạo spending evidence.

## Bước tiếp tục

1. Chốt agent/model/provider, caps và runtime/API architecture theo [gói quyết định hiện có](stage7-decision-package.md).
2. Triển khai binding cụ thể, đưa gate thực vào loader; kiểm config/usage/error/SDK retries và ledger tiền thực có version. Không đổi nhãn SIM_USD hoặc gỡ guard cũ để chạy model.
3. Review task, kiểm isolation/cleanup/attestation và đóng băng manifest scope. Chỉ dùng credential trong đúng process/client cần nó.
4. Khi đủ điều kiện, chạy smoke 1–2 trial trong cap riêng, reconcile billing, rồi pilot 72 trial khi review 6/6 và budget cho phép.

Không tự chọn model, giá, ngân sách, reviewer hoặc runtime thay người phụ trách. Không hỏi lại quyết định đã có trong phiên; phần phụ thuộc vẫn thiếu được giữ đúng trạng thái. Các client/API surface và mapping usage chưa có agent cụ thể để kiểm được để mở trong [kế hoạch giai đoạn 8](../Plan/plan-giai-doan-8.md).

Bằng chứng máy đọc: [inventory](stage8-input-state.json), [credential metadata](stage8-credential-status.json), [test Linux](stage8-unit-tests.json); tổng hợp tại `reports/stage8-summary.json`.
