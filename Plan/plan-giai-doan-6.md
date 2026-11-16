# Kế hoạch giai đoạn 6 — Ngân sách dùng chung, reconciliation và kết nối provider thực

- Ngày lập: 12/11/2026.
- Trạng thái cập nhật 12/11/2026: G6.1–G6.2 offline đã đạt; G6.3–G6.4 chờ đầu vào và kiểm định thực. Các mốc model trước đó tiếp tục mở.
- Kế thừa: [giai đoạn 5](plan-giai-doan-5.md), [readiness hiện tại](../reports/stage5-readiness.md), [bằng chứng bàn giao](../reports/stage5-summary.json), [hợp đồng executor](../docs/model-executor-contract.md).
- Mục tiêu gần nhất: đóng hai khoảng trống kỹ thuật còn có thể xử lý offline — ngân sách dùng chung giữa các run và quy trình xử lý request/partial trial chưa rõ trạng thái.
- Mục tiêu có điều kiện: kết nối đúng agent/provider được chọn, hoàn tất review/runtime thực, chạy smoke rồi native pilot. G4.3–G4.5 và G5.3–G5.5 tiếp tục mở cho tới khi có bằng chứng tương ứng.

**Kết quả triển khai:** 126/126 test Linux đạt, 0 skip. Đã nối ledger pool/run với executor fixture qua outbox, bổ sung receipt revision/CLI reconciliation và billing overlay. Integration bản cuối có hai request fixture/bốn revision, kiểm crash/replay, số dư chung và restore năm DB; model/API calls thật = 0. Xem [readiness giai đoạn 6](../reports/stage6-readiness.md), [kiểm định billing](../reports/shared-billing-offline-validation.md), [ledger contract](../docs/shared-billing-ledger.md) và [runbook](../docs/reconciliation-runbook.md).

Phạm vi đạt là SIM_USD/offline. Chưa có account/provider/budget thực, xác thực provider receipt, remote lookup/cancel hoặc checkpoint recovery thực. Partial thiếu checkpoint giữ uncertain; review vẫn 0/6. Những phần phụ thuộc provider/reviewer/runtime thực tiếp tục để mở.

## 1. Điểm xuất phát và giới hạn công việc

Đã có sáu task B development, instruction EN/VI, verifier và bằng chứng kỹ thuật; review độc lập vẫn **0/6**, độ khó provisional. Giai đoạn 5 đạt **102/102 test Linux**, integration CLI hai trial fixture qua ba attempt/năm request, có kiểm tra resume và restore. Chưa có model/API call thật.

Executor hiện chỉ có binding fixture. `--mode model` trả readiness, không dispatch; manifest tự sinh vẫn là preview. Đã có gate trước request, ledger attempt/request và source provenance, nhưng chưa có ledger chung cho smoke/pilot cùng ngân sách, chưa có recovery policy thực cho mọi partial multi-request. JSON policy chưa chứng minh agent isolation hoặc provider billing thực tế.

Phần offline giai đoạn này giới hạn ở các khoảng trống trên. Giữ nguyên sáu task, các archive/report lịch sử và template review đã có. Chỉ bổ sung kiểm định cho hành vi mới; không đặt mục tiêu tăng số test hoặc chạy lại 72 trial giả lập để thay reviewer và cấu hình thực.

## 2. Mốc nghiệm thu và phụ thuộc

| Mốc | Sản phẩm | Điều kiện đạt |
|---|---|---|
| G6.1 — Ngân sách dùng chung offline | Billing scope, reservation/settlement liên run và kiểm định cạnh tranh | Smoke/pilot không cùng tiêu một phần ngân sách; uncertain không tự giải phóng tiền |
| G6.2 — Reconciliation/recovery offline | Báo cáo request chưa rõ, receipt import và recovery có audit | Giữ lịch sử, không tự resend; chỉ tiếp tục khi có bằng chứng đủ và gate hiện tại đạt |
| G6.3 — Binding và bằng chứng thực | Hai cấu hình, review, provider adapter, runtime/isolation và pricing | Có agent/provider được chọn và bằng chứng từ nguồn thực; fixture không tạo pass cho phần này |
| G6.4 — Smoke/pilot thực | Smoke riêng scope, sau đó native pilot 72 trial | Đúng budget/phạm vi, raw/usage/cost/coverage đối chiếu được |

Nếu vẫn thiếu reviewer/model/budget, có thể hoàn thành G6.1–G6.2 trong phạm vi offline và bàn giao rõ phần còn thiếu. Không đánh dấu G6.3–G6.4 hoặc các mốc model cũ đã hoàn tất từ kết quả này.

## 3. T0 — Bảo toàn đầu vào và phân công quyết định

- [x] Đối chiếu snapshot task/prompt, archive/report giai đoạn trước và source hashes đã kiểm. Ghi inventory giai đoạn 6 ở output mới; không ghi đè report cũ.
- [x] Dùng lại [template model](../configs/model-pilot.template.json) và [template review](../configs/review-records.stage5.template.json), ghi đúng trường đã được cung cấp và trường vẫn thiếu.
- [x] Ghi trạng thái có kiểu `pass`, `fail`, `missing_input`, `unverified`, `not_applicable`, kèm thời điểm, scope, nguồn bằng chứng và hành động tiếp theo.
- [x] Tách yêu cầu quyết định của chủ dự án khỏi công việc kỹ thuật có thể tiếp tục. Không hỏi lại chỉ vì sang giai đoạn mới.

| Đầu vào | Vai trò cung cấp | Có thể làm trước khi có đầu vào |
|---|---|---|
| Reviewer độc lập và thời gian review | Chủ dự án chỉ định; kỹ sư Việt Nam khác tác giả thực hiện | Kiểm hash và tính đầy đủ của hồ sơ hiện có |
| Hai agent/model/version, prompt, tools và kiến trúc API | Chủ dự án/đội Eval | Hợp đồng billing/recovery trung lập với provider |
| Caps smoke/pilot, phạm vi dùng chung ngân sách và billing account reference | Chủ dự án | Kiểm schema và tranh chấp bằng SIM_USD |
| Runtime profile được chọn | Người vận hành | Kiểm validator; không tự bật relay/root |
| Credentials theo cơ chế đã chọn | Người vận hành | Thiết kế luồng cấp secret; offline không đọc giá trị |
| Snapshot/config/quyền dùng phần A | Đội Eval | Giữ checklist hiện có, tiếp tục phần B |

Tên vai trò không phải chỉ định danh tính người thực hiện. Không tự điền reviewer, model, account hoặc giá API. Nếu người dùng đã cung cấp quyết định và phạm vi chạy trong phiên, dùng lại quyết định đó, không tạo vòng xác nhận trùng lặp.

**Bàn giao dự kiến:** `reports/stage6-input-state.json`; danh sách thiếu có thể đối chiếu với template, không tạo acceptance hoặc profile thực giả.

## 4. T1 — Ledger ngân sách chung giữa smoke và pilot

### Định danh và phạm vi

- [x] Định nghĩa `billing_scope_id`, account reference không chứa secret, currency/unit, run ID, execution scope và request/attempt identity. Xác định rõ hai run có dùng chung một pool ngân sách hay không.
- [x] Giữ trần riêng của smoke/pilot đồng thời áp trần chung của billing scope. Khi hai cấu hình thuộc account/provider khác nhau, mô tả rõ chúng dùng pool chung hay riêng theo quyết định thực.
- [x] Cách ly hoàn toàn SIM_USD khỏi tiền thực. Không cộng khác currency hoặc tự đặt tỷ giá; nếu cần quy đổi phải có policy/nguồn xác minh trước thực thi.
- [x] Phân biệt phần cấu hình đóng băng với số dư thay đổi: billing scope, cap và policy có version; balance/receipt cập nhật không tạo một model configuration mới mỗi lần.

### Transaction và phí chưa rõ

- [x] Chọn một nguồn ledger có thẩm quyền cho reservation dùng chung; kiểm đồng thời trần run và trần pool trước dispatch. Hai controller không thể cùng reserve phần tiền còn lại.
- [x] Nếu local attempt DB và ledger chung là hai DB, thiết kế intent/outbox cùng quy trình reconcile. Không giả định hai transaction SQLite riêng là một transaction nguyên tử.
- [x] Giữ mapping reservation → request → receipt và cập nhật idempotent. Resume không tạo thêm reservation cho cùng request đã đăng ký.
- [x] Ghi chi phí bằng số nguyên micro-unit hoặc Decimal theo schema đã chốt, có nguồn giá/usage. Null tiếp tục là unknown, không chuyển thành 0.
- [x] Request uncertain vẫn giữ exposure phù hợp. Khi dùng chung pool, smoke còn request chưa rõ phải được tính/chặn theo policy trước khi pilot tiêu tiếp; external uncertainty không bị trạng thái local xóa.
- [x] Chỉ giải phóng reservation khi có căn cứ chưa submit hoặc có kết quả settlement đủ. Hết lease, timeout hoặc mất process không chứng minh request chưa được nhận/charge.
- [x] Khi actual vượt reserve/cap, giữ nguyên phí đã biết, ghi overrun và chặn dispatch mới. Không hứa trần cứng cho phí provider chưa xác nhận hoặc request đang chạy.
- [x] Lưu ledger trên filesystem phù hợp transaction/locking; có backup/restore nhất quán và ownership rõ. Không sửa hoặc migrate archive giai đoạn 4–5 tại chỗ.

### Kiểm định tối thiểu

- [x] Hai run khác scope cùng reserve gần cap: chỉ reservation còn đủ tiền được nhận.
- [x] Smoke đã charge hoặc còn uncertain làm thay đổi đúng ngân sách pilot trong cùng pool; pool độc lập không bị gộp nhầm.
- [x] Crash giữa ghi intent chung và ghi state local: reconcile không mất exposure hoặc tính hai lần.
- [x] Cùng receipt nhập lại không cộng phí lần nữa; null, actual 0 và overrun vẫn phân biệt được.
- [x] Restore ledger/local state cho phép đối chiếu tổng phí và reservation theo run/request.

**Bàn giao dự kiến:** schema billing scope, thành phần ledger dùng chung và report kiểm định có nhãn offline. Không cần một lượt simulation 72 trial mới để chứng minh các trường hợp này.

## 5. T2 — Reconciliation và recovery cho request/partial trial

Trước hết tạo công cụ quan sát và nhập bằng chứng. Khả năng tiếp tục tự động phải dựa vào semantics của adapter thực; không suy từ SQLite fixture sang provider.

- [x] Thêm lệnh read-only liệt kê submitted/uncertain, attempt/request liên quan, lease, receipt đã có, phí đã biết và reservation còn giữ.
- [x] Định nghĩa receipt import với nguồn, thời điểm, run/account/request identity, provider request ID nếu có và hash raw evidence. Reject sai scope/identity hoặc receipt xung đột không có cơ sở điều chỉnh.
- [x] Giữ event history append-only. Khi cập nhật phân loại hoặc billing, lưu cả nguồn cũ, nguồn mới và lý do; không ghi lại lịch sử thành “chưa từng submit”.
- [x] Phân biệt kết quả task đã biết nhưng billing chưa rõ với request chưa rõ kết quả. Reward hợp lệ không mất chỉ vì hóa đơn chưa xác định; báo tài chính chưa hoàn tất riêng.
- [x] Receipt đầy đủ của request đã gửi cho phép settle/reconcile, không dispatch lại request đó.
- [x] “Lookup không thấy”, provider timeout hoặc cancellation chưa xác nhận không đủ để kết luận chưa charge. Adapter chưa hỗ trợ lookup phải báo capability thiếu và giữ uncertain.
- [ ] Partial multi-request chỉ được tiếp tục khi xác định được request đã nhận, request chưa gửi, agent checkpoint/tool state và cách bảo toàn trial identity. Trạng thái agent không phục hồi được thì giữ phần thiếu để điều tra, không tái chạy từ đầu như chưa phát sinh phí.
- [x] Trước request mới sau recovery, kiểm lại snapshot/config, review, runtime còn hạn và ngân sách hiện tại. Reconciliation không phải token vượt gate.
- [ ] Nếu một thao tác lookup/cancel thực cũng gọi provider hoặc có thể tính phí, đưa nó vào policy/accounting tương ứng; không giả định read-only local fixture và remote lookup có cùng đặc tính.

| Tình huống | Xử lý dự kiến |
|---|---|
| Reserved và chứng minh chưa submit | Có thể claim tiếp hoặc hủy reservation theo policy |
| Submitted, chưa có receipt đủ tin cậy | Giữ uncertain/exposure, không resend |
| Receipt đầy đủ, harness chưa persist | Nhập/reconcile receipt, không gọi lại model |
| Kết quả cuối đã biết, cost thiếu | Giữ kết quả; giữ billing uncertainty và reservation phần chưa rõ |
| Một phần request đã xong, checkpoint thiếu | Giữ trial chưa hoàn tất; không tự chạy lại toàn bộ |
| Receipt điều chỉnh phí | Ghi revision có nguồn và diff, cập nhật số dư một lần |

- [x] Kiểm định nhập receipt lặp, sai identity, evidence conflict, checkpoint thiếu và gate fail sau recovery. Test đi qua command/orchestrator sử dụng thực tế, không chỉ helper độc lập.

**Bàn giao dự kiến:** `docs/reconciliation-runbook.md`, CLI quan sát/reconcile và report offline. Phần provider-specific vẫn unverified nếu chưa có provider được chọn.

## 6. T3 — Review và binding agent/provider thực, có điều kiện

### Review task

- [ ] Chủ dự án chỉ định reviewer theo [hướng dẫn](../docs/review-guide.md); mở public trước reference, giải độc lập và đo thời gian thực.
- [ ] Thu nhận xét EN/VI, fixture/expected/verifier, lỗi và quyết định gắn hash. Dùng importer hiện có; fixture signoff và template còn trống không tạo accepted.
- [ ] Nếu task cần sửa, tăng version khi đổi hợp đồng, review/kiểm định lại đúng phạm vi và giữ EN–VI đối xứng. Không chạy lại toàn bộ task không bị ảnh hưởng.
- [ ] Smoke chỉ dùng task đã accepted trong scope; pilot chính thức cần đủ 6/6. Giữ độ khó provisional khi chưa đủ bằng chứng.

### Binding và account thực

- [ ] Nhận hai cấu hình thực và phạm vi chi tiêu; chọn đúng agent/provider/version trước khi triển khai API client. Không tự chọn model mặc định để đi qua gate.
- [ ] Đọc source/tài liệu chính thức của adapter đã chọn, khóa dependency phù hợp và ghi mọi thay đổi pin cần thiết.
- [ ] Thay binding fixture bằng adapter cụ thể qua factory/registry được kiểm soát trong code. JSON không được tùy ý import module hoặc bật dispatch chỉ bằng một nhãn `agent-verified`.
- [ ] Thu effective config từ quá trình khởi tạo agent thật: model/endpoint/effort, prompt content, kwargs allowlist, tools, resource, timeout và API architecture.
- [ ] Đối chiếu request identity của harness với client/provider request ID, usage, exception và artifact. Chỉ coi importer Harbor hiện có tương thích khi đã kiểm đúng output/version mới.
- [ ] Kiểm các retry ẩn của SDK/agent: tắt hoặc đưa chúng vào trace/accounting và policy phù hợp. Retry ở client không được làm mất lượt gọi/chi phí hoặc vượt giao thức retry đã chốt.
- [ ] Xác minh giá hiện hành khi đã có model/provider: nguồn/ngày, currency/unit, cached token/tool fees và phí lỗi liên quan. Không dùng fixture pricing làm estimate thực.
- [ ] Nối billing scope thực và cơ chế cấp secret. Chỉ đọc secret trên đường cần thực thi sau các kiểm tra cần thiết; không log giá trị hoặc đưa chúng vào fingerprint/report.
- [ ] Kiểm định lookup, idempotency, cancellation và checkpoint recovery theo capability thật. Không hỗ trợ thì công bố giới hạn và giữ hành vi conservative tương ứng.

**Nghiệm thu:** G6.3 cần review và bằng chứng agent/provider thực. Đủ trường trong profile hoặc test SDK mock pass chưa đủ để gọi adapter là đã kiểm thực tế.

## 7. T4 — Runtime và API isolation thực

- [ ] Người vận hành chọn rõ profile trong [runtime catalog](../configs/runtime-profiles.json), bắt đầu concurrency 1; không tự chuyển endpoint hoặc root khi profile hiện tại fail.
- [ ] Kiểm distro/user/endpoint, CLI/engine hiện tại, filesystem Linux, resource limits và kiến trúc host-agent/container-agent tương ứng lựa chọn.
- [ ] Kiểm agent không tiếp cận oracle/expected/verifier kín hoặc Docker control socket. Verifier phải offline; API credentials/egress đúng policy được thực thi, không chỉ khai báo trong JSON.
- [ ] Thu attestation mới đúng run/snapshot/profile trước dispatch. Khi hết hạn thì kiểm lại trước request mới; kết quả và phí request đã gửi vẫn được lưu.
- [ ] Kiểm heartbeat/lease của controller và quyền claim. Lease hết hạn không được cấp quyền resend một request provider có thể vẫn đang xử lý.
- [ ] Thử cleanup khi hoàn tất, lỗi và hủy: chỉ tài nguyên thuộc run; bảo toàn raw/ledger phục vụ reconciliation. Không restart/prune workload chung.
- [ ] Nếu cần tăng concurrency, kiểm runtime và reservation dùng chung trước; test CAS offline không chứng minh container/API concurrency mới đã đạt.

Default WSL socket vẫn có lịch sử gián đoạn. Relay stage3 là workaround development; chỉ dùng khi đã được chọn và kiểm lại theo run. Không mô tả giai đoạn này như đã sửa triệt để default integration nếu chưa có bằng chứng.

## 8. T5 — Smoke rồi native pilot thật

**Điều kiện bắt đầu:** cấu hình/provider/budget thực đã có trong phạm vi chạy, review theo scope đạt, binding và runtime phù hợp đã kiểm, manifest thực được đóng băng và gate hiện tại đạt. Viết kế hoạch hoặc tạo preview không tự cấp quyền paid run.

- [ ] Smoke có run ID, scope `model-smoke`, 1–2 trial và trần riêng; khi có hai cấu hình, ưu tiên một trial mỗi cấu hình và ghi rõ tổ hợp chưa smoke.
- [ ] Kiểm auth/model ID, tools, artifact transfer, reward, usage/billing, ledger chung và cleanup. Reward 0 do giải sai vẫn là kết quả task hợp lệ, không phải lý do chọn lại task tới khi pass.
- [ ] Reconcile request/chi phí smoke còn uncertain trước khi pilot dùng cùng ngân sách theo policy. Không tăng caps hoặc giả cost 0 để tiếp tục.
- [ ] Sau smoke đạt, đóng băng pilot B: **6 task × 2 instruction × 3 repeat × 2 cấu hình = 72 trial**, chưa gồm smoke/retry; môi trường và lịch sử độc lập, seed/thứ tự ghi rõ.
- [ ] Kiểm gate và reservation trước request, giữ mọi attempt/cost; tối đa hai retry bổ sung theo giao thức, không best-of-three. Khi điều kiện không còn đạt, dừng phần chưa gửi và giữ thông tin request đang chạy.
- [ ] Xuất raw/normalized/provenance/ledger, archive Linux có checksum và restore proof; báo coverage hợp lệ, missing/infra/uncertain cùng số dư.
- [ ] Tính macro theo [giao thức](../docs/evaluation-protocol.md), delta EN–VI và hạn chế. Một family/skill chưa đủ CI B; repeat không tạo family mới.
- [ ] Viết smoke report và `reports/native-model-pilot.md` bằng kết quả thực. Run thiếu coverage được báo là một phần; không điền kết quả giả để hoàn tất mốc.

Các quyết định model/budget/phạm vi đã được người dùng cung cấp trong phiên được giữ hiệu lực; không thêm vòng xác nhận trùng lặp. Thiếu dữ liệu hoặc vượt phạm vi ngân sách thì chỉ dừng phần phụ thuộc tương ứng và ghi lý do cụ thể.

## 9. T6 — Phần A, tập kín và phát hành

- [ ] Phần A giữ `missing_input` tới khi có [đầu vào Eval](../docs/eval-input-checklist.md); kiểm quyền dùng, snapshot/verifier và khả năng đối chiếu baseline trước khi dịch/chạy.
- [ ] Nếu đủ đầu vào, sáu task A × bốn instruction × ba repeat × hai cấu hình thêm 144 trial. Tách A/B; không gọi subset là toàn bộ Terminal-Bench 4.0.
- [ ] Sáu task B hiện tại vẫn là development. Dùng lỗi pilot để quyết định private families theo [thiết kế hiện có](../docs/private-test-design.md), chưa mở rộng task để thay công việc review/binding còn thiếu.
- [ ] License, hosting, phát hành và gửi dữ liệu ra ngoài là nhánh có điều kiện riêng; không phát sinh upload/publish từ kế hoạch này.

## 10. Thứ tự, thời gian và sản phẩm bàn giao

```text
T0 → T1 ngân sách chung → T2 reconciliation offline ─────────────────┐
T3 review + cấu hình + binding thực ─────────────────────────────────┤
T4 runtime/isolation thực ──────────────────────────────────────────┤
                                                                  └→ T5 smoke → pilot
T6 A/private/release: nhánh có điều kiện, không chặn T1–T2 offline.
```

| Công việc | Ước lượng ngày làm việc | Phụ thuộc chính |
|---|---:|---|
| T0 và thiết kế T1 | 1 | Không cần model/API key |
| Ledger chung, crash/concurrency tests | 2–3 | Hợp đồng billing scope |
| T2 CLI reconcile và kiểm định | 1–2 | Identity/receipt schema và ledger |
| Bàn giao readiness mới | 1 | Bằng chứng của phần đã thực hiện |
| Review, binding/provider và runtime thực | Ước lượng sau khi có đầu vào | Người review, cấu hình, account/budget, môi trường |
| Smoke/pilot | Theo timeout, tài nguyên và budget thực | T3/T4 và gate đạt |

Khoảng 5–7 ngày cho nhánh offline là ước lượng lập kế hoạch, không gồm thời gian chờ đầu vào. Chưa ước tính giá API khi chưa có model/provider/nguồn giá xác minh.

Sản phẩm dự kiến: inventory giai đoạn 6, schema billing/recovery, thành phần ledger/CLI, report test/integration thực tế và `reports/stage6-readiness.md`. Nếu chưa có provider thực, report phải ghi 0 model calls và giới hạn fixture; không tạo smoke/pilot report giả.

## 11. Definition of Done và điểm dừng

- [x] Bằng chứng lịch sử, task/prompt và trạng thái review được bảo toàn; report mới có scope/thời điểm/source.
- [x] Các run dùng chung pool không thể reserve vượt tổng cap; actual/unknown/reservation đối chiếu được giữa ledger chung và local state.
- [x] Crash, receipt lặp và backup/restore không làm mất exposure hoặc tính phí hai lần.
- [x] Có CLI quan sát/reconcile dùng được; recovery giữ audit, không tự resend và không vượt gate.
- [x] Model/simulation và tiền thực/SIM_USD tiếp tục tách biệt; regression liên quan đạt, số test/call báo từ kết quả thực.
- [x] Báo rõ reviewer/model/budget/runtime/binding còn thiếu; G6.1–G6.2 offline không tự hoàn tất G6.3–G6.4.
- [ ] Khi có đầu vào thực: review, effective adapter, API isolation, pricing/accounting và runtime đã kiểm trước smoke.
- [ ] Chỉ sau chạy thật: có smoke/pilot report, ledger, raw archive và coverage đúng thực tế; cập nhật các mốc model cũ theo bằng chứng.
- [x] A/private/release giữ deferred nếu chưa đủ điều kiện; không có thay đổi task, upload hoặc phát hành ngoài phạm vi.

**Bắt đầu khi triển khai:** T0, sau đó T1 và công cụ read-only của T2. Dùng các case fixture nhỏ để kiểm khoảng trống mới. Khi thiếu đầu vào thực, kết thúc nhánh offline bằng báo cáo cụ thể và giữ nguyên trạng thái chưa chạy model.
