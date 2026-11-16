# Hợp đồng executor và scope — giai đoạn 5

Trạng thái: đã có orchestration và adapter fixture bền vững; **chưa có binding provider thực**. `scripts/model_executor.py` mặc định validate; `--mode model` cũng chỉ xuất readiness và trả code 2. Không có API client, secret loader hay cơ chế import plugin từ JSON. `pilot_runner.py --mode model` vẫn giữ guard cũ.

## Scope và manifest

`execution_contracts.py` tạo schema `vi-execution-manifest/0.1` từ dry-run hiện có, snapshot hiện tại và execution policy. Các trường chính: kind/origin/scope, run/snapshot ID, planned trials, expected configurations, configuration fingerprints, policy hash và manifest hash. Mỗi trial có ba attempt đã lập trước; retry không tạo repeat mới.

| Scope | Phạm vi | Review bắt buộc | Ngân sách |
|---|---|---|---|
| `model-smoke` | 1–2 trial ID chọn rõ từ preview; đủ hai cấu hình không phải điều kiện của mọi smoke con | Các task được chọn, đúng hash | Trần inference/compute riêng, tổng không vượt smoke cap |
| `native-pilot` | Đúng 72 trial, đủ hai cấu hình × EN/VI × ba repeat × sáu task | 6/6 người review độc lập | Caps inference/compute pilot |
| Fixture offline | Kind `simulation`, origin `offline-fixture`, có scope mục tiêu để kiểm hợp đồng | Signoff `reviewer_kind=fixture`; không nhập được vào review thật | SIM_USD, nguồn giá giả lập |

Manifest smoke và pilot là hai run riêng khi chạy thực. Hệ thống chưa có ledger tài khoản provider dùng chung; nếu dùng chung ngân sách/account phải kiểm tổng exposure và request uncertain giữa các scope khi triển khai binding thật. Chưa đáp ứng điều kiện đó thì không dispatch thật.

Profile vẫn dùng template native-six hiện có để định nghĩa hai cấu hình so sánh. Smoke chọn subset theo trial ID, không sửa profile thành một pilot ít task rồi báo đủ coverage. Manifest được dựng lại để kiểm tra snapshot, prompt, config, policy, ID và attempt routing; thay bất kỳ phần nào phải tạo run mới.

## Mapping và provenance

Fingerprint gồm model profile, system prompt content hash, stable runtime profile hash, concurrency, tools/resource policy và request bound/reservation. Thời điểm attestation và endpoint relay tạm không nằm trong stable hash. Policy hiện chỉ khai báo terminal tool và resource từ `task.toml`, verifier network none; fixture không chứng minh enforcement thực tế.

`FixtureAdapter.inspect()` đọc cấu hình hiệu lực từ file settings riêng mỗi lần gate, không lấy expected context rồi gắn nhãn observed. Vì đây vẫn là settings mô phỏng, observation luôn có origin `offline-fixture`. Nó thu adapter ID/version, hash các source tham gia, run/snapshot, config/policy hashes và capabilities.

Capabilities fixture: accounting từng request; số request tối đa mỗi attempt; lookup receipt SQLite cục bộ; không giả định idempotency; không có real pricing hoặc cancellation. Không có registry provider thực. Một file ghi `agent-verified` hoặc `ready=true` không thể tự bật provider binding.

Khi có adapter thực, các thao tác cần triển khai/kiểm định là:

1. Validate schema/kwargs của đúng agent/version và xây cấu hình hiệu lực từ quá trình khởi tạo thật.
2. Thu provenance từ source/runtime đáng tin cậy và kiểm isolation/egress; so sánh với expected config.
3. Gửi request có identity và receipt/usage/artifact mapping rõ ràng; thu phí kể cả lỗi billable.
4. Khai báo và kiểm định lookup, retry, timeout/cancellation đúng khả năng provider; không suy từ fixture sang provider thật.
5. Nối secret tại đường dispatch đã kiểm, chỉ ghi tên cơ chế cấp secret và dữ liệu đã loại secret vào report.

## Gate trên đường thực thi

`Executor.run_one()` đọc lại context và settings trước reserve/claim attempt và trước từng request. Gate kiểm profile, origin, manifest, review theo scope, attestation hiện tại, observed config/provenance, budget và provider binding. Các lần check không tạo API call.

Context đổi sau preview không được tái sử dụng preview pass như quyền thực thi. Runtime attestation phải đúng run/snapshot/profile và còn hạn; fixture runtime chỉ là dữ liệu test. Gate trả `ready_for_model_dispatch=false` ở mọi chế độ hiện có, ngay cả khi `ready_for_dispatch=true` cho fixture offline.

Các kiểm tra này không phải xác thực mật mã hay bảo đảm môi trường không thể thay đổi sau check. Executor thực tương lai phải thu evidence từ đúng đường khởi tạo và thực thi policy; không chỉ đọc một JSON do người gọi tự khai.

## Ledger attempt và request

Executor fixture dùng lại SQLite `Store` giai đoạn 4 trong namespace simulation và thêm bảng `execution_requests` ở state mới. Không sửa hoặc migrate archive stage4. Frozen plan gắn manifest, policy, caps/reservation và source hash; resume khác các trường này bị từ chối.

Reservation attempt được ghi trước submit; request có reservation, request ID, CAS claim, owner/lease và receipt riêng. Chỉ một attempt được submitted tại một thời điểm giữa các controller C1. Mỗi request kiểm lại phần bound còn trong attempt. Overrun ở request trước có thể chặn request kế tiếp trong cùng trial; phí đã quan sát vẫn lưu.

Các trạng thái chưa rõ kết quả hoặc cost giữ uncertain. Request null cost giữ reservation; reward đã biết của kết quả cuối vẫn được giữ khi normalized. Request/attempt raw và event log giữ riêng để thấy phí đã biết ngay cả khi tổng attempt còn chưa xác định.

Lease mặc định 30 giây. Crash sau receipt được reconcile từ fake-provider SQLite, không gửi lại. Submit không có receipt và partial multi-request chưa hoàn tất giữ uncertain, **không tự tiếp tục hoặc resend**. Hiện chưa có cơ chế tự phục hồi mọi trường hợp partial multi-request; cần recovery policy theo provider khi có binding thật. Lookup ở fixture chỉ đọc receipt cục bộ, không đại diện cho một API lookup có thể phát sinh phí.

Retry chỉ với infra/verifier đã phân loại, tối đa ba attempt; agent failure không retry để đổi reward. Event, raw request, raw attempt, normalized và tổng phí phải đối chiếu được. Chi phí giả không chuyển thành USD thực.

## Dữ liệu ra và kiểm định

State có hai SQLite DB và `export/`: raw attempts, normalized trials, events, `requests.jsonl`, summary và `executor-provenance.json`. Provenance ghi hash source, target scope, origin fixture và tổng phí request đã biết. Chuỗi raw → normalized → aggregate vẫn dùng namespace simulation; aggregator từ chối model smoke đưa vào pilot scoring.

Các đầu vào fixture có `reviewer_kind=fixture` và runtime `data_origin=offline-fixture`. [Review template](../configs/review-records.stage5.template.json) có record còn null; không phải acceptance. Không áp các file này vào manifest dataset thật.

Xem [hướng dẫn CLI](model-executor.md) và [readiness giai đoạn 5](../reports/stage5-readiness.md) để phân biệt kết quả kiểm định đã có với những điều kiện vẫn thiếu.
