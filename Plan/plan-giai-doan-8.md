# Kế hoạch giai đoạn 8 — Cấp credential OpenAI và tích hợp đường chạy model thật

- Ngày lập: 12/11/2026.
- Trạng thái cập nhật 13/11/2026: V0 và phần loader/redaction/source-policy của V2 đã kiểm offline; 150/150 test Linux đạt. G8.2 chưa hoàn tất binding/config; chưa chạy API/model thật.
- Kế thừa: [giai đoạn 7](plan-giai-doan-7.md), [readiness trước đó](../reports/stage7-readiness.md), [gói quyết định](../reports/stage7-decision-package.md), [hợp đồng billing](../docs/shared-billing-ledger.md).
- Đầu vào mới: người dùng cung cấp OpenAI API key để lưu trong `.env`, với tên biến `OPENAI_API_KEY`.
- Mục tiêu: nối credential vào agent/provider adapter được chọn, kiểm config/runtime/billing, rồi chạy smoke và pilot khi đủ điều kiện.

**Kết quả đợt triển khai:** G8.1 đạt cho credential storage; thêm loader theo process, diagnostic an toàn và source-artifact policy, giữ nguyên các guard cũ. Có 24 test mới, toàn bộ 150 test trên native Linux đạt, không skip; `.env` thật không được copy/hash vào snapshot hoặc đọc giá trị trong đợt này. Xem [readiness](../reports/stage8-readiness.md), [kiểm định](../reports/credential-loader-validation.md), [tài liệu loader](../docs/credential-loading.md) và [inventory](../reports/stage8-input-state.json).

Agent/model/budget/runtime và review vẫn thiếu; chưa có SDK client factory hoặc binding thực. Những phần request/usage/SDK retry, config hiệu lực và API/billing thực tiếp tục để mở bên dưới. Loader helper không phải cơ chế tự cấp quyền model dispatch.

## 1. Trạng thái hiện tại

| Thành phần | Trạng thái |
|---|---|
| `.env` tại root dự án | Đã tạo với `OPENAI_API_KEY`; không ghi giá trị vào kế hoạch/report |
| Git | `.env` được ignore và chưa được track |
| Key có hợp lệ/quyền model/quota không | Chưa kiểm qua API |
| Agent và hai cấu hình model | Chưa chốt; không suy ra model từ việc đã có key |
| Budget/account/pool thực | Chưa chốt; key không xác nhận phạm vi chi tiêu |
| Runtime model | Chưa chọn/kiểm định theo run |
| Review task | 0/6 accepted |
| API/model call trong đợt này | 0 |

Nguồn OpenAI Docs đã đối chiếu: [Authentication](https://developers.openai.com/api/reference/overview#authentication) hướng dẫn giữ API key bí mật và cấp qua environment/secret manager phía server; [SDKs and CLI](https://developers.openai.com/api/docs/libraries) mô tả SDK đọc key từ environment.

File `.env` là nơi lưu cục bộ. Đã có helper nạp tường minh sau gate, nhưng executor model chưa được nối với helper qua provider binding thực và key chưa được xác thực. Đây là tiến độ về credential, không phải G7.1 hoặc readiness model đã đạt.

Key đã xuất hiện trong hội thoại; người sở hữu nên thu hồi và tạo key mới trước khi dùng thật, sau đó thay giá trị trong `.env` cục bộ. Kế hoạch chỉ ghi tên biến, không lưu bản sao, fingerprint hoặc đoạn trích của secret.

## 2. Mốc và điều kiện nghiệm thu

| Mốc | Sản phẩm | Điều kiện đạt |
|---|---|---|
| G8.1 — Credential cục bộ | `.env` chứa tên biến đúng và được Git bỏ qua | Đã đạt cho việc lưu file; auth/quota vẫn chưa xác minh |
| G8.2 — Cấu hình và binding OpenAI | Agent/model đã chọn, config hiệu lực, credential loader và client mapping | Offline validation đạt, secret không lọt vào output; không coi mock pass là API thật đã kiểm |
| G8.3 — Runtime/billing/kết nối thực | Runtime, nguồn giá, ledger tiền thực và request/usage/receipt | Đủ cơ sở reservation, scope/budget rõ và evidence từ đường gọi thật |
| G8.4 — Smoke benchmark | 1–2 trial có review, budget riêng | Auth/tools/verifier/artifact/accounting/cleanup đạt |
| G8.5 — Native pilot B | 72 trial và báo cáo | Review 6/6, coverage và phí đối chiếu được; báo phần thiếu nếu chưa hoàn tất |

G8.1 không mở dispatch tự động. Các mốc model còn mở của giai đoạn 4–7 chỉ cập nhật khi bằng chứng thật đáp ứng đúng scope.

## 3. V0 — Bảo toàn credential và bằng chứng

- [x] Tạo `.env` theo yêu cầu, dùng tên biến `OPENAI_API_KEY`.
- [x] Kiểm tra giá trị hiện diện bằng kiểm tra cục bộ, không in nội dung hoặc gọi API.
- [x] Xác nhận `.env` được Git ignore và không bị track.
- [x] Khi triển khai tiếp, đối chiếu snapshot/task/source/report giai đoạn trước và lập inventory mới không chứa secret.
- [x] Kiểm đường đóng gói artifact/source, diagnostic và lỗi không đưa `.env`, key hoặc Authorization header vào archive/report/log.
- [x] Nếu tạo `.env.example`, chỉ để placeholder rỗng; không copy giá trị thật từ `.env`.

Không export key toàn hệ thống hoặc đưa vào Docker build argument/image. Khi thay key, chỉ thay ở nguồn secret cục bộ được chọn; báo cáo chỉ thể hiện trạng thái credential, không ghi giá trị hoặc hash key.

## 4. V1 — Chốt agent/model và phạm vi chi tiêu

- [ ] Chọn hai cấu hình theo [template hiện có](../configs/model-pilot.template.json): agent/version, model ID, provider, effort hoặc không áp dụng, prompt/tools và giới hạn.
- [ ] Dùng `credential_env_name=OPENAI_API_KEY` cho cấu hình OpenAI khi cấu hình đó được chọn. Chưa suy rằng cả hai cấu hình cùng OpenAI hoặc cùng project chỉ vì một key đã được cung cấp.
- [ ] Xác minh endpoint/version/kwargs từ source/tài liệu chính thức của agent/provider đã chọn. Không lấy model trong ví dụ tài liệu làm model mặc định của benchmark.
- [ ] Chốt caps smoke, inference/compute pilot, cap pool, account reference không chứa secret, currency và scope được phép chạy.
- [ ] Chọn runtime/API architecture, prompt content và giới hạn token/turn/time/resource/concurrency. Giữ EN–VI tương đương trong từng cấu hình.
- [ ] Lập profile theo run ID mới; lưu source của quyết định và các trường chưa biết. Template cũ giữ nguyên làm tài liệu schema.

OpenAI SDK là client gọi API; agent terminal vẫn cần được chọn và mapping tools/sandbox phải được triển khai. Có key không xác định được agent, model được phép dùng hoặc ngân sách. Nếu người dùng đã cung cấp những quyết định này trong phiên, dùng lại thay vì hỏi xác nhận trùng lặp.

## 5. V2 — Credential loader và adapter OpenAI

### Nạp secret đúng đường thực thi

- [x] Chọn cơ chế nạp `.env` tường minh vào environment của process cần key; không thực thi file như shell script và không tự bật key cho mọi subprocess.
- [x] Quy định ưu tiên giữa environment đã cấp và `.env`; không âm thầm ghi đè credential do người vận hành đã chọn.
- [x] Preview/dry-run và test offline không đọc key thật. Dùng secret giả được inject cho test loader, redaction và lỗi thiếu credential.
- [x] Chỉ cấp key cho host agent hoặc thành phần API được chọn; verifier và container task offline không nhận key nếu không có nhu cầu trong kiến trúc đã chốt.
- [x] Thiếu biến, giá trị rỗng hoặc lỗi nạp cấu hình phải dừng bằng thông báo không lộ secret. Không gửi key trong argv, URL query, manifest, fingerprint hoặc debug dump.

### Client và agent mapping

- [ ] Chọn/khóa official SDK hoặc client của adapter thực theo source/version; chỉ thêm dependency cần thiết cho đường đã chọn.
- [ ] Xác định API surface theo khả năng của agent/model đã chọn; đối chiếu schema thực trước khi nối request/tools/usage. Không giả định mọi agent dùng cùng API.
- [ ] Thu effective config từ khởi tạo agent, so model/effort/prompt/kwargs/tools/resource với expected config.
- [ ] Theo dõi từng request hoặc chứng minh upper bound từ token/turn/tool limits. Retry ẩn của SDK/agent phải được tắt hoặc đưa vào trace/accounting.
- [ ] Thu client/provider request ID, usage, error và artifact cần thiết. API Overview mô tả request ID phục vụ debug; chỉ log metadata cần thiết, không log Authorization/key. [OpenAI Docs](https://developers.openai.com/api/reference/overview#debugging-requests).
- [ ] Nối registry/factory trong code và gate thực; không mở model bằng việc đổi nhãn fixture hoặc xóa guard cũ.

### Kiểm định offline trước network

- [x] Key giả không lọt vào exception/report/artifact; real `.env` không được đưa vào test snapshot.
- [ ] Gate fail tạo 0 lời gọi client; config drift, thiếu model/budget hoặc runtime evidence phải bị phát hiện.
- [ ] Kiểm request/usage/error mapping và SDK retry bằng fixture có nguồn; giữ unknown cost/status thay vì ép về 0.
- [x] Bảo toàn fixture/SIM_USD và các report cũ. Version hóa source/schema cho run mới; audit lịch sử đối chiếu đúng source snapshot, không sửa bằng chứng cũ để khớp code mới.

**Bàn giao dự kiến:** credential loader, binding theo agent đã chọn, effective-config diff và report offline. Chưa có auth/provider receipt thật thì ghi unverified.

## 6. V3 — Billing và runtime thực

- [ ] Xác minh giá hiện hành của model đã chọn khi chuẩn bị chạy; lưu nguồn/ngày, unit, token/cache/tool fees và trường usage liên quan. Chưa điền giá API vào kế hoạch này.
- [ ] Triển khai schema/ledger tiền thực phù hợp binding đã kiểm. `billing_ledger.py` hiện từ chối USD; không đổi nhãn SIM_USD để vượt giới hạn đó.
- [ ] Áp cap run/pool và reserve trước request. Account/project balance hoặc giới hạn provider chưa xác minh không được suy từ key có mặt trong file.
- [ ] Nối receipt/usage từ đường provider thực với request/run/account; dùng source evidence đủ tin cậy, không chỉ JSON tự khai có hash.
- [ ] Kiểm timeout, unknown response, rate limit, phí lỗi và khả năng lookup/cancel/idempotency theo adapter thực. Không nhận được response không chứng minh chưa charge.
- [ ] Người vận hành chọn runtime profile, kiểm engine/user/endpoint, filesystem Linux, resource và API egress/isolation. Giữ verifier offline và Docker control socket ngoài agent/verifier.
- [ ] Capture attestation mới theo run/snapshot/profile; kiểm lại khi hết hạn. Bảo toàn kết quả/phí request đã gửi và cleanup đúng tài nguyên run.

Nếu cần một request kiểm tra kết nối riêng trước benchmark, phải có model và budget/scope dành cho kiểm tra đó, thu usage/chi phí và gắn nhãn riêng. Kết quả chỉ xác nhận kết nối trong phạm vi đã thử; không thay review task, không nhập vào điểm smoke/pilot và không nới gate benchmark để chạy thử.

## 7. V4 — Review và smoke benchmark

- [ ] Chủ dự án giao reviewer kỹ sư Việt Nam khác tác giả, dùng [review guide](../docs/review-guide.md) và [record template](../configs/review-records.stage5.template.json).
- [ ] Thu record người thật với hash/time/nhận xét/decision. Giữ attribution `Codex-assisted`; fixture signoff không tạo accepted.
- [ ] Chọn 1–2 trial từ các task đã review, lập manifest `model-smoke` và trần smoke riêng. Runtime/binding/reservation/gate phải đạt trước dispatch.
- [ ] Chạy với môi trường sạch, kiểm auth/model ID, tools, artifact, verifier, usage/receipt, shared billing và cleanup.
- [ ] Phân biệt task fail với lỗi provider/infra; giữ mọi attempt và phí. Reward 0 hợp lệ không phải lý do đổi task tới khi model pass.
- [ ] Reconcile request/cost uncertain theo [runbook](../docs/reconciliation-runbook.md), bổ sung provider-specific policy đã kiểm. Chưa có checkpoint thì không tự chạy lại partial trial.
- [ ] Xuất report smoke và archive Linux có checksum/source/receipt. Chỉ gọi đây là model smoke khi đã có kết quả thực.

## 8. V5 — Native pilot và các nhánh sau pilot

- [ ] Review đủ 6/6, hai cấu hình đã kiểm, smoke đạt và budget pilot đã có trong phạm vi cho phép.
- [ ] Đóng băng **6 task × 2 instruction × 3 repeat × 2 cấu hình = 72 trial**, chưa gồm smoke/retry; ghi seed, planned IDs, snapshot và attempt routing.
- [ ] Gate/reserve trước request; giữ mọi attempt/cost, tối đa hai retry bổ sung theo giao thức. Không best-of-three hoặc retry lời giải sai.
- [ ] Báo coverage valid/missing/infra/uncertain theo cấu hình/ngôn ngữ/task/repeat. Dừng phần chưa gửi khi điều kiện không còn đạt.
- [ ] Xuất raw/normalized, provenance, ledger/overlay; đối chiếu phí revision hiện tại và delta, không cộng các revision như nhiều request mới.
- [ ] Tính macro/delta EN–VI theo [giao thức](../docs/evaluation-protocol.md). Một family/skill vẫn chưa đủ CI B; giữ null và lý do khi chưa thể ước lượng.
- [ ] Archive Linux, kiểm checksum/restore và viết báo cáo model pilot thực hoặc báo rõ phần chưa hoàn tất.
- [ ] Phần A tiếp tục chờ [snapshot/config Eval](../docs/eval-input-checklist.md); private families và phát hành là nhánh có điều kiện riêng sau pilot.

## 9. Thứ tự triển khai và điểm dừng

```text
V0 lưu credential (đã thực hiện)
  → V1 chốt agent/model/budget/runtime
  → V2 loader + binding theo lựa chọn
  → V3 billing/runtime thực
  → V4 review theo scope + smoke
  → V5 review 6/6 + pilot 72 trial
```

Review có thể tiến hành trong lúc triển khai binding/runtime. Phần độc lập trước khi có model/budget là cơ chế nạp secret, redaction và kiểm config bằng secret giả; không cần dùng key thật để tạo thêm simulation.

Nếu vẫn thiếu agent/model/budget, bàn giao phần chuẩn bị đã kiểm và danh sách thiếu cụ thể. Không thực hiện auth probe hoặc inference chỉ để thử key vừa được lưu. Khi đã có quyết định và scope chi tiêu trong phiên thì tiếp tục trong scope đó, không thêm vòng xác nhận trùng lặp.

| Công việc | Thời gian ước lượng |
|---|---|
| V0 lưu key và kiểm Git ignore | Đã thực hiện trong đợt lập kế hoạch |
| Loader/redaction/config offline | Khoảng 0,5–1 ngày nếu không đổi kiến trúc |
| Binding, billing và runtime thực | Ước lượng sau khi chọn agent/model/API architecture |
| Review | Theo reviewer và thời gian giải thực |
| Smoke/pilot | Theo timeout, tài nguyên và budget đã chốt |

Chưa ước tính tiền API hoặc thời gian hoàn tất provider integration khi chưa có cấu hình cụ thể. Sản phẩm dự kiến gồm inventory giai đoạn 8 không chứa secret, binding/config evidence, report readiness và smoke/pilot report nếu đã thực thi.

## 10. Definition of Done

- [x] Credential được lưu vào `.env`, Git ignore và không bị track; chưa gọi API.
- [x] Loader/diagnostic/archive không làm lộ key; preview và test offline tiếp tục dùng dữ liệu giả phù hợp.
- [ ] Agent/model/budget/account/runtime được chọn rõ; presence của key không tự tạo auth/quota/spending evidence.
- [ ] Binding, effective config, SDK retries, pricing/usage/receipt và ledger tiền thực được kiểm theo nguồn thực tương ứng.
- [ ] Runtime/isolation/cleanup có bằng chứng theo run; gate còn hiệu lực trước request.
- [ ] Smoke và pilot chỉ được đánh dấu đạt bằng kết quả thực và coverage/chi phí đúng thực tế.
- [x] Lịch sử/source/task được bảo toàn; review vẫn cần người thật; A/private/release giữ deferred nếu chưa đủ điều kiện.

**Việc tiếp theo khi triển khai:** nạp credential đúng process và kiểm redaction bằng key giả, đồng thời hoàn tất V1. Giá trị key thật chỉ nằm trong nguồn secret cục bộ; không đưa vào report để chứng minh đã có credential.
