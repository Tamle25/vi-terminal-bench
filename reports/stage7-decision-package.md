# Gói quyết định để bắt đầu run model

Ngày chuẩn bị: 12/11/2026. Phạm vi: U0 và phần chuẩn bị U1 của [kế hoạch giai đoạn 7](../Plan/plan-giai-doan-7.md).

Bằng chứng kỹ thuật hiện có đã được đối chiếu lại. Các lựa chọn thực vẫn chưa có: review độc lập **0/6**, **27 trường profile/budget còn null**, runtime chưa chọn. **G7.1 = missing_input; chưa chạy model.** Gói này dùng để chốt đầu vào, không phải manifest thực thi hoặc quyết định chi tiền.

## 1. Những quyết định cần cung cấp trước

| Quyết định | Nội dung cần cung cấp | Vai trò cung cấp | Trạng thái |
|---|---|---|---|
| Reviewer | Kỹ sư Việt Nam khác tác giả, task được giao và thời gian có thể review | Chủ dự án/reviewer | Chưa chỉ định |
| Cấu hình A | Agent, model ID, provider và mục tiêu cấu hình so sánh | Chủ dự án/đội Eval | Chưa có |
| Cấu hình B | Agent, model ID, provider và điểm khác với A | Chủ dự án/đội Eval | Chưa có |
| Ngân sách | Trần smoke, inference/compute pilot; pool chung hay riêng và trần pool | Chủ dự án | Chưa có |
| Billing | Account reference không chứa secret, currency và scope được phép chạy | Chủ dự án/người vận hành | Chưa có |
| Runtime | Profile native/relay và API từ host hay container | Người vận hành | Chưa chọn |
| Prompt/tools/limits | System prompt hoặc yêu cầu cần dùng, tool access, token/turn/time/resource | Người quyết định cấu hình + kỹ sư triển khai | Chưa chốt |
| Credentials | Cơ chế cấp secret hoặc tên biến; không gửi giá trị vào repo/report | Người vận hành | Chưa chốt |

Có thể cung cấp agent/model/provider trước nếu chưa biết version hoặc endpoint tương thích. Khi có lựa chọn đó, kỹ sư sẽ đối chiếu source/tài liệu chính thức, lập mapping và các đề xuất kỹ thuật có nguồn. Những trường này hiện vẫn để trống, không tự điền bằng một model hay giá API giả định.

Các quyết định đã cung cấp trong phiên tiếp tục có hiệu lực. Hiện thông tin người dùng xác nhận chưa có vẫn được giữ nguyên; gói này không yêu cầu lặp lại câu trả lời đó.

## 2. Điền vào template hiện có

Dùng [model-pilot.template.json](../configs/model-pilot.template.json). Khi đủ lựa chọn thực, tạo file theo run ID mới, ví dụ `configs/model-pilot.<run-id>.json`; giữ template gốc để tra schema.

| Trường cho từng `candidate-a` / `candidate-b` | Giá trị hiện tại | Nội dung cần chốt |
|---|---|---|
| `agent` | null | Agent cụ thể |
| `agent_version` | null | Version/source revision đã khóa |
| `model` | null | Model ID cụ thể |
| `provider` | null | Provider tương ứng |
| `endpoint` | null | Endpoint hỗ trợ, không nhúng credentials/query secret |
| `reasoning_effort` | null | Giá trị adapter hỗ trợ hoặc `not-applicable` có cơ sở |
| `system_prompt_path` | null | File Markdown trong workspace; ghi hash nội dung |
| `max_tokens` | null | Giới hạn theo semantics của adapter |
| `max_turns` | null | Giới hạn vòng thực thi |
| `timeout_sec` | null | Timeout agent, phân biệt lỗi hạ tầng |
| `architecture` | null | Host agent/sandbox offline hoặc container agent/egress được kiểm |
| `credential_env_name` | null | Tên biến/cơ chế cấp secret, không phải giá trị secret |

24 trường trên thuộc hai cấu hình. Ba trường budget còn thiếu là `max_inference_usd`, `max_compute_usd`, `smoke_max_usd`. Đơn vị trong tên trường là hợp đồng của template, chưa phải bằng chứng có budget/account được chọn. Nếu cần currency khác, phải version hóa hợp đồng và cách tính, không tự quy đổi.

Template đang có EN/VI, ba repeat, concurrency 1 và hai ID `candidate-a`/`candidate-b`. Đây là giá trị chuẩn bị development; chưa chứng minh runtime model đã được kiểm. `agent_kwargs` giữ `{}` tới khi có allowlist của đúng adapter. Ngoài template, cần ghi quyết định billing scope/account, cap pool, tool/resource policy và phạm vi smoke/pilot vào gói run thực sau này.

## 3. Giao review theo snapshot hiện tại

Snapshot ID: `490323ee9077ad81f00c2468a69ecd45884cba7caafb0a1dca1f1507b8679288`.

| Task | Version | Reviewer / quyết định |
|---|---|---|
| B001 — hóa đơn VND/ngày | 0.1.0 | Chưa có / pending |
| B002 — file Unicode NFC/NFD | 0.1.0 | Chưa có / pending |
| B003 — Windows-1258 | 0.1.0 | Chưa có / pending |
| B004 — tìm kiếm không dấu | 0.1.0 | Chưa có / pending |
| B005 — collation tiếng Việt | 0.1.0 | Chưa có / pending |
| B006 — CSV tiếng Việt | 0.1.0 | Chưa có / pending |

Dùng [review template chứa hash](../configs/review-records.stage5.template.json) và [review guide](../docs/review-guide.md). Mở [public bundle](../jobs/stage3-review-public.tar.gz) trước, giải độc lập/đo thời gian, rồi đối chiếu [reference bundle](../jobs/stage3-review-reference.tar.gz). Đây là bàn giao nội bộ, chưa gửi gói ra ngoài.

Reviewer ghi đủ record thực theo [schema](../docs/pilot-state-schema.md), xuất JSON array rồi validate bằng `review_records.py`. Chỉ `--apply` mới nhập accepted; không chạy import khi mới có mẫu chưa điền. Accepted phải khớp task version/payload và cả prompt EN/VI. Giữ attribution `Codex-assisted`; review không thay đổi nguồn gốc tác giả.

Smoke cần accepted cho các task được chọn; pilot cần đủ 6/6. Nếu có changes requested, sửa/version hóa và kiểm định phần bị ảnh hưởng trước khi đóng băng snapshot mới.

## 4. Chọn runtime và kiến trúc API

[Runtime catalog](../configs/runtime-profiles.json) hiện có `selected_runtime_profile=null`.

| Lựa chọn đã định nghĩa | Bằng chứng hiện có | Việc phải làm trước model run |
|---|---|---|
| `native-wsl-v1` | Default socket có lịch sử gián đoạn | Chọn profile, kiểm CLI/engine/user/endpoint và capture mới theo run |
| `desktop-relay-v1` | Relay command-only đã kiểm development ở giai đoạn 3 | Chọn rõ profile, bảo đảm lifecycle/quyền vận hành và kiểm lại cho run thật |

Runtime control plane và đường gọi API model là hai phần cần đối chiếu riêng. Cần chọn host agent thao tác sandbox offline hoặc container agent có egress được thực thi, đồng thời giữ verifier offline. Profile có JSON policy chưa chứng minh isolation; capture cũ không thay preflight hiện tại.

## 5. Vị trí tiếp tục khi có đầu vào

| Đầu vào đã có | Tiếp tục trong kế hoạch | Sản phẩm cần thu |
|---|---|---|
| Reviewer được giao | U2 | Record thật, hash/time/nhận xét và review coverage |
| Hai cấu hình, cap/account | U1 → U3 | Profile theo run, adapter/version, effective-config diff và pricing/usage mapping |
| Runtime/API architecture | U4 | Bằng chứng isolation/cleanup và attestation còn hạn |
| Task smoke đã review, binding/runtime/budget đạt | U5 | 1–2 trial smoke thật, raw/reward/usage/cost và receipt |
| Smoke đạt, review đủ 6/6, budget pilot đã có | U6 | 72 trial B hoặc báo phần thiếu đúng thực tế |

Provider binding thực hiện chưa tồn tại; core model guard vẫn giữ nguyên. Ledger SIM_USD, receipt fixture và file preview không bật được đường gọi model. Auth/usage/receipt chưa thể xác nhận hoàn toàn trước smoke sẽ được ghi vào kiểm định smoke có giới hạn khi đã có binding và reservation đủ cơ sở.

Phần A tiếp tục chờ [đầu vào Eval](../docs/eval-input-checklist.md). Sáu task hiện tại vẫn là development; private set và phát hành chưa bắt đầu.

Chi tiết inventory và trường thiếu ở [stage7-input-state.json](stage7-input-state.json). Readiness sau chuẩn bị ở [stage7-readiness.md](stage7-readiness.md).
