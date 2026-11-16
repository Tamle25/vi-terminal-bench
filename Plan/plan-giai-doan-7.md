# Kế hoạch giai đoạn 7 — Chốt cấu hình, kết nối agent thật và chạy pilot đầu tiên

- Ngày lập: 12/11/2026.
- Trạng thái cập nhật 12/11/2026: U0 và phần chuẩn bị U1 đã hoàn thành; G7.1 vẫn `missing_input`, G7.2–G7.4 chưa đạt/chưa chạy vì chưa có đầu vào thực.
- Kế thừa: [giai đoạn 6](plan-giai-doan-6.md), [readiness hiện tại](../reports/stage6-readiness.md), [tổng hợp bằng chứng](../reports/stage6-summary.json).
- Mục tiêu chính: hoàn tất đầu vào con người/cấu hình, kiểm định một đường thực thi agent/provider cụ thể và thu kết quả model đầu tiên.
- Điều kiện: reviewer, hai cấu hình, ngân sách/account và runtime thực phải được cung cấp hoặc lựa chọn trong phạm vi người dùng cho phép. Các mốc model còn mở của giai đoạn 4–6 chỉ hoàn tất bằng bằng chứng thực tương ứng.

**Kết quả đợt chuẩn bị:** đã đối chiếu snapshot/bằng chứng giai đoạn 6 và kiểm workspace. Review vẫn 0/6, 27 trường profile/budget còn null, runtime chưa chọn; không có cấu hình thực mới để triển khai binding. Đã bàn giao [inventory](../reports/stage7-input-state.json), [gói quyết định](../reports/stage7-decision-package.md) và [readiness](../reports/stage7-readiness.md). Không chạy lại bộ test/simulation, không gọi model hoặc tự điền các quyết định còn thiếu. 126 test Linux là bằng chứng kế thừa, không phải run mới của giai đoạn 7.

## 1. Điểm xuất phát và ưu tiên

Đã có sáu task B development với instruction EN/VI, oracle/verifier và bằng chứng kỹ thuật. Giai đoạn 6 đạt **126/126 test Linux**, có ledger ngân sách chung, outbox, receipt revision, billing overlay và CLI reconciliation. Integration hai request fixture/bốn receipt revision đã kiểm crash/replay và restore năm DB. Chưa có model/API call thật.

Đường găng hiện tại là review độc lập **0/6**, hai cấu hình/budget còn thiếu, provider binding và runtime thực chưa kiểm định. Ledger hiện chỉ hỗ trợ SIM_USD fixture; `--mode model` vẫn chỉ validate. Hạ tầng offline chưa phải bằng chứng rằng một agent thật có thể chạy và được hạch toán đúng.

Giai đoạn 7 ưu tiên chốt và thực hiện các điều kiện này. Tái sử dụng các hợp đồng, template, ledger và runbook đã có; chỉ bổ sung code/test khi cần cho adapter cụ thể hoặc lỗi thực phát hiện. Giữ nguyên quy mô sáu task trước pilot, không đặt mục tiêu tăng test count hoặc tạo thêm một lượt simulation 72 trial.

## 2. Mốc và điều kiện nghiệm thu

| Mốc | Sản phẩm | Điều kiện đạt |
|---|---|---|
| G7.1 — Đầu vào thực | Reviewer được giao, hai cấu hình, budget/account và runtime được chọn | Có quyết định thực theo scope, không dùng placeholder hoặc người review giả |
| G7.2 — Đường thực thi đã kiểm | Review theo scope, adapter, effective config, billing và isolation | Bằng chứng từ agent/runtime thực; phần chưa chứng minh được ghi rõ và đủ điều kiện cho smoke có giới hạn |
| G7.3 — Smoke model | 1–2 trial, budget riêng, raw/usage/receipt đầy đủ | Auth/tools/verifier/accounting/cleanup đúng; uncertainty được xử lý trước khi mở rộng |
| G7.4 — Native pilot B | 72 trial theo hai cấu hình, EN/VI và ba repeat | Coverage, reward, lỗi, retry và phí đối chiếu được; báo phần thiếu nếu run chưa hoàn tất |

Nếu đầu vào vẫn chưa có, chỉ hoàn thiện inventory và gói quyết định còn thiếu của U0–U1. G7.1 vẫn `missing_input`, các mốc sau chưa đạt. Đây là điểm dừng bàn giao cho nhánh phụ thuộc, không phải lý do tạo thêm một hệ thống phụ offline hoặc tự chọn model/ngân sách thay chủ dự án.

## 3. U0 — Đóng băng bằng chứng và chuẩn bị gói run

- [x] Kiểm snapshot sáu task/prompt, source và archive/report theo bằng chứng giai đoạn 6. Dùng report mới, giữ nguyên lịch sử.
- [x] Ghi `reports/stage7-input-state.json`: thời điểm, scope/run reference, snapshot, nguồn và trạng thái có kiểu cho từng điều kiện.
- [x] Dùng lại [template model](../configs/model-pilot.template.json), [template review](../configs/review-records.stage5.template.json), [ledger contract](../docs/shared-billing-ledger.md) và [runbook](../docs/reconciliation-runbook.md).
- [x] Chuẩn bị một gói quyết định ngắn, chỉ rõ trường cần điền, vai trò cung cấp, phần đã biết và nơi tiếp tục khi có đầu vào. Chưa có quyết định thì giữ null/pending.
- [x] Ghi rõ phần người dùng đã xác nhận chưa có; không hỏi lại cùng thông tin chỉ vì sang giai đoạn mới.

**Bàn giao dự kiến:** inventory và `reports/stage7-decision-package.md`. Chưa tạo profile model hoàn chỉnh, reviewer accepted hoặc ngân sách thực giả.

## 4. U1 — Chốt đầu vào để chạy thật

| Quyết định | Nội dung cần có | Vai trò cung cấp |
|---|---|---|
| Review | Người khác tác giả, thời gian review và task được giao | Chủ dự án/reviewer |
| Hai cấu hình | Agent/version, model ID, provider/endpoint, effort hoặc không áp dụng | Chủ dự án/đội Eval |
| Prompt và tools | System prompt theo nội dung/hash, kwargs được hỗ trợ, tool access và giới hạn | Kỹ sư triển khai cùng người quyết định cấu hình |
| Ngân sách | Caps smoke/pilot/pool, currency, phạm vi chi tiêu và account reference | Chủ dự án |
| Runtime | Profile native/relay, user, tài nguyên, concurrency và API architecture | Người vận hành |
| Credentials | Cơ chế cấp secret hoặc tên biến; không ghi giá trị vào repo | Người vận hành |

- [ ] Điền hai cấu hình cụ thể vào file theo run ID mới khi đã có quyết định thực. Hai cấu hình phải phân biệt rõ được điều kiện so sánh.
- [ ] Chốt EN–VI có cùng ngân sách và policy trong mỗi cấu hình. Ghi đối tượng được đánh giá là model + agent + tools + budget, không suy thành năng lực model độc lập.
- [ ] Chốt pool dùng chung hay riêng cho smoke/pilot và cho hai cấu hình. Account reference chỉ là reference không chứa secret; chưa có lựa chọn thì chưa tạo pool tiền thực.
- [ ] Chốt giới hạn token/turn/time/resource/concurrency và trường không áp dụng dựa trên adapter thực, không âm thầm bỏ qua field agent không hỗ trợ.
- [ ] Lưu quyết định và nguồn trong gói run; không coi preview hoặc file `ready=true` là quyền tự chạy paid workload.

Khi người dùng đã cung cấp cấu hình/budget và phạm vi chạy trong phiên, dùng lại quyết định đó, không tạo vòng xác nhận trùng lặp. Viết kế hoạch này chưa phải cung cấp những đầu vào đang thiếu hoặc cho phép tăng budget.

**Nghiệm thu G7.1:** có đầu vào thực, người phụ trách review và cấu hình đủ để triển khai đúng adapter. Nếu mới có một cấu hình, ghi phạm vi thử riêng; không gọi đó là pilot 72 trial hai cấu hình đã đầy đủ.

## 5. U2 — Review độc lập theo snapshot

- [ ] Reviewer mở instruction/public trước reference, giải trên môi trường sạch, ghi thời gian thực đo và điểm mơ hồ.
- [ ] Kiểm EN/VI theo cùng ràng buộc, fixture/expected/verifier, false positive/negative, alternative solution và artifact transfer.
- [ ] Ghi reviewer, ngày, task version/payload/prompt hashes, expert time, nhận xét và `accepted` hoặc `changes_requested` bằng schema hiện có.
- [ ] Validate/import record thật. Oracle/control pass, fixture signoff và template còn trống không tạo accepted.
- [ ] Nếu cần sửa hợp đồng task, tăng version, cập nhật cả EN/VI khi liên quan và kiểm định lại đúng phạm vi; accepted của snapshot cũ không dùng cho task mới.
- [ ] Giữ attribution `Codex-assisted` đúng lịch sử. Review của kỹ sư Việt Nam không tự biến nguồn gốc task thành tuyên bố do người viết nguyên bản.
- [ ] Smoke chỉ dùng task đã review trong scope; pilot chính thức phải đủ 6/6. Độ khó tiếp tục provisional nếu chưa đủ bằng chứng để hiệu chỉnh.

**Bàn giao:** record thực và coverage theo snapshot. Không gửi bundle, reference hoặc dữ liệu ra ngoài khi chưa có chỉ dẫn tương ứng.

## 6. U3 — Triển khai binding của agent/provider được chọn

Chỉ bắt đầu phần provider-specific sau U1. Dùng source/tài liệu chính thức của đúng adapter/version khi triển khai; không tự chọn SDK/model chỉ để nối được API.

### Version và bảo toàn lịch sử

- [ ] Lưu source snapshot/hash cho run mới; khóa agent/Harbor/dependency cần thiết. Nếu chưa có Git commit, dùng source archive có SHA-256, không tự tạo danh tính Git.
- [ ] Version hóa binding/schema thay đổi. Validator lịch sử phải đối chiếu source của đúng snapshot/archive; không sửa report cũ để khớp source mới.
- [ ] Giữ fixture namespace/ledger cũ độc lập. Triển khai đường tiền thực theo binding và schema được kiểm, không đổi nhãn SIM_USD thành USD hoặc xóa guard để mở dispatch.

### Mapping, request và usage

- [ ] Xây factory/registry kiểm soát trong code cho adapter được chọn; JSON không được tùy ý import module hoặc tự cấp nhãn trusted binding.
- [ ] Thu effective config từ quá trình khởi tạo agent thật: model/provider/endpoint/effort, prompt content hash, kwargs allowlist, tools, resource và architecture.
- [ ] Đối chiếu expected/effective trước request. Chọn rõ agent gọi API từ host hay trong container và nơi giữ secret.
- [ ] Thu request intent/client ID/provider ID, usage, exception, artifact và provenance thực. Không coi thiếu response ID là bằng chứng provider chưa nhận request.
- [ ] Kiểm retry ẩn của SDK/agent và các lời gọi model/tool billable khác. Tắt hoặc đưa chúng vào accounting/policy; số request tính phí không được bị che bởi một attempt tổng.
- [ ] Nếu không quan sát được từng request, chứng minh được upper bound reservation từ giới hạn thực thi. Chưa có bound đủ cơ sở thì chưa dispatch smoke.
- [ ] Kiểm raw output mới với importer hiện có theo đúng Harbor/agent version; mở rộng adapter nếu cần, không mặc định mọi output đều tương thích.

### Tiền thực và receipt

- [ ] Xác minh giá tại thời điểm chạy khi model/provider đã chọn: nguồn/ngày, currency/unit, token/cache/tool fees và phí lỗi liên quan. Chưa có dữ liệu thì giữ unknown.
- [ ] Nối caps run và pool thực với reservation/settlement; phân biệt budget của harness với balance provider account. Không suy balance thực từ reference ID hoặc số dư fixture.
- [ ] Thu receipt/usage từ đường provider đáng tin cậy và liên kết request/run/account. Hash raw JSON chỉ chứng minh tính nhất quán, không tự xác thực nguồn provider.
- [ ] Báo known subtotal, exposure, uncertainty và adjustment riêng; giữ legacy task raw và authoritative billing overlay để tránh cộng phí hai lần.
- [ ] Kiểm lookup/idempotency/cancel/checkpoint theo capability thật. Không hỗ trợ thì giữ recovery conservative; negative lookup hoặc timeout không tự cho phép resend.
- [ ] Chỉ đọc secret ở đường cần thực thi sau các kiểm tra phù hợp. Giá trị secret không vào argv/log/manifest/fingerprint/report.

**Bàn giao dự kiến:** binding cụ thể, source/version, effective-config diff, mapping raw/usage/receipt và report kiểm định. Mock/test contract đạt chưa được gọi là provider thực đã kiểm hoàn toàn.

## 7. U4 — Kiểm runtime và policy thực thi

- [ ] Người vận hành chọn rõ profile trong [runtime catalog](../configs/runtime-profiles.json); bắt đầu concurrency 1, không tự chuyển sang relay/root khi default fail.
- [ ] Kiểm distro/user/endpoint, CLI/engine hiện tại, filesystem Linux hỗ trợ case/NFC/NFD và resource/timeout thực.
- [ ] Kiểm agent không đọc oracle/expected/test kín hoặc Docker control socket. Verifier offline; egress/API/secret đúng policy được thực thi.
- [ ] Capture attestation mới theo run/snapshot/profile; hết hạn thì kiểm lại trước request mới, không làm mất kết quả/phí request đã gửi.
- [ ] Kiểm owner/lease/heartbeat và nguồn receipt khi controller lỗi. Lease hết hạn không chứng minh request provider đã ngừng xử lý.
- [ ] Thử cleanup bình thường, lỗi và hủy: chỉ tài nguyên thuộc run, giữ ledger/raw cho reconciliation, không restart hoặc prune workload chung.
- [ ] Nếu đổi pin runtime/resource hoặc tăng concurrency, kiểm phạm vi ảnh hưởng bằng probe/control nhỏ phù hợp; không lặp toàn bộ task khi không cần.

Default WSL socket còn lịch sử gián đoạn. Relay stage3 chỉ là workaround development; cần chọn và kiểm lại cho run thực. JSON policy và test SQLite cạnh tranh không thay thế bằng chứng isolation/container/API.

**Nghiệm thu G7.2:** có review đúng scope, effective binding/runtime và cơ sở reservation đủ cho smoke có giới hạn. Phần auth/usage/receipt chỉ xác nhận được qua smoke phải được ghi rõ trong kế hoạch smoke, không tạo evidence giả để qua gate.

## 8. U5 — Smoke model đầu tiên

**Điều kiện bắt đầu:** cấu hình và budget smoke đã có trong phạm vi cho phép, task được review, binding/runtime đạt kiểm tra cần thiết, manifest scope smoke đóng băng và gate trước dispatch đạt.

- [ ] Lập run ID mới, scope `model-smoke`, 1–2 trial và cap riêng. Khi có hai cấu hình, ưu tiên một trial mỗi cấu hình; ghi rõ ngôn ngữ/task và tổ hợp chưa smoke.
- [ ] Thu config/provenance trước chạy, môi trường sạch và lịch sử độc lập; không tái dùng output hoặc trajectory fixture.
- [ ] Kiểm auth/model ID, tools, artifact transfer, verifier reward, usage/cost, shared budget và cleanup.
- [ ] Phân loại lỗi task/agent/provider/infra rõ ràng; giữ mọi attempt và phí billable. Reward 0 do giải sai là kết quả hợp lệ, không phải lý do đổi task tới khi pass.
- [ ] Reconcile request/cost còn uncertain trước khi pilot dùng chung pool theo policy. Không ép unknown thành 0 hoặc tự tăng cap để tiếp tục.
- [ ] Viết `reports/model-smoke.md` và archive Linux có checksum/source/receipt. Smoke chưa đạt thì điều tra đúng lỗi, không chuyển thẳng sang pilot.

**Nghiệm thu G7.3:** đường thực thi, chấm, accounting và provenance đúng trong phạm vi smoke. Smoke không tạo điểm năng lực đại diện hoặc bao phủ mọi tổ hợp của pilot.

## 9. U6 — Native pilot B và báo cáo

- [ ] Review đủ 6/6, hai cấu hình đã kiểm, budget pilot có trong phạm vi và shared ledger không còn uncertainty chặn dispatch.
- [ ] Đóng băng **6 task × 2 instruction EN/VI × 3 repeat × 2 cấu hình = 72 trial**, chưa gồm smoke/retry; lưu planned IDs, snapshot, attempt routing và source/runtime contracts.
- [ ] Ghi seed/thứ tự đã trộn, môi trường sạch và lịch sử riêng mỗi trial; ngân sách EN–VI tương đương trong mỗi cấu hình.
- [ ] Gate/reserve trước request; tối đa hai retry bổ sung theo giao thức, giữ mọi raw/attempt/cost. Không retry lời giải sai hoặc lấy best-of-three.
- [ ] Dừng phần chưa gửi khi budget/runtime/evidence không còn đạt; giữ kết quả và phí của request đã gửi để reconcile.
- [ ] Xuất raw/normalized/provenance cùng ledger/overlay; tổng phí lấy revision hiện tại, không cộng cả phí cũ lẫn toàn bộ revision mới. Reward đã biết và billing chưa rõ được báo riêng.
- [ ] Báo coverage theo task/config/language/repeat, valid/missing/infra/uncertain và chi phí đã biết/chưa biết. Nếu thiếu trial hoặc còn infra unresolved, báo pilot một phần/provisional.
- [ ] Tính macro theo [giao thức](../docs/evaluation-protocol.md), delta EN–VI trên điều kiện khớp và taxonomy lỗi. Một family/skill vẫn chưa đủ CI B; repeat không tạo family mới.
- [ ] Archive trên filesystem Linux để bảo toàn Unicode/case, kiểm checksum và restore dữ liệu. Ghi giới hạn checkpoint/khả năng resume thay vì suy mọi archive đều tiếp tục chạy được sau di chuyển.
- [ ] Viết `reports/native-model-pilot.md`: cấu hình/version/ngày, kết quả thực, denominator, billing, giới hạn development set và kết luận có phạm vi.

**Nghiệm thu G7.4:** kết quả thực có đủ bằng chứng hoặc báo chính xác phần chưa hoàn tất. Chỉ cập nhật các mốc model cũ đã đạt đúng scope; không coi smoke hoặc subset là pilot 72 trial hoàn chỉnh.

## 10. U7 — Phần A, private families và phát hành

- [ ] Phần A chờ [đầu vào Eval](../docs/eval-input-checklist.md): snapshot/quyền dùng, task/verifier/config và baseline có thể đối chiếu.
- [ ] Nếu đủ đầu vào, sáu task A × bốn instruction × ba repeat × hai cấu hình thêm 144 trial; tách kết quả A/B, không gọi subset là toàn bộ Terminal-Bench 4.0.
- [ ] Sáu task B hiện tại vẫn là development. Sau pilot, dùng lỗi thực và khoảng trống đo lường để quyết định [private families](../docs/private-test-design.md) và quy mô mở rộng.
- [ ] License, hosting, gửi dữ liệu ra ngoài và phát hành là nhánh có điều kiện riêng; không phát sinh upload/publish từ việc lập hoặc thực hiện phần offline của kế hoạch này.

## 11. Thứ tự, thời gian và điểm dừng

```text
U0 → U1 quyết định thực ──┬→ U2 review ──────────────────────────┐
                        ├→ U3 agent/provider/billing thực ─────┤
                        └→ U4 runtime/isolation thực ──────────┤
                                                             └→ U5 smoke → U6 pilot
U7 A/private/release: nhánh có điều kiện, không chặn phần B.
```

| Công việc | Ước lượng | Phụ thuộc |
|---|---|---|
| U0 và gói quyết định U1 | Khoảng 1 ngày kỹ thuật | Có thể chuẩn bị với bằng chứng hiện có |
| Chốt quyết định và review | Theo người phụ trách được giao | Reviewer, lịch làm việc và thời gian giải thực |
| Binding/provider/billing U3 | Ước lượng sau khi chọn cấu hình | Agent/provider/API architecture cụ thể |
| Runtime/isolation U4 | Khoảng 1–2 ngày sau khi chọn profile, điều chỉnh nếu có lỗi thực | Môi trường và quyền vận hành phù hợp |
| Smoke | 1–2 trial theo timeout/cap thực | G7.2 và budget smoke |
| Pilot | 72 trial theo timeout/concurrency/budget thực | Smoke đạt, review 6/6 và budget pilot |

Chưa ước tính giá API hoặc cam kết số ngày hoàn tất provider integration khi chưa có cấu hình. Chưa có reviewer/model/budget thì bàn giao gói quyết định với `missing_input` cụ thể; không triển khai một binding giả khác để đánh dấu tiến độ model.

Sản phẩm dự kiến: inventory/gói run, review coverage thực, binding/effective-runtime/pricing evidence, report smoke/pilot nếu đã chạy và `reports/stage7-readiness.md`. Không tạo report kết quả model nếu chưa thực thi.

## 12. Definition of Done

- [x] Snapshot, attribution, report/archive và source lịch sử được bảo toàn theo đúng phiên bản.
- [x] Có gói quyết định rõ trường thiếu; G7.1 chỉ đạt khi có người/cấu hình/budget/runtime thực.
- [ ] Review accepted gắn đúng hash và đủ theo scope; fixture hoặc oracle pass không thành review người thật.
- [ ] Binding được kiểm với đúng agent/provider, effective config, request/usage mapping, pricing/billing và capability thực; giới hạn chưa kiểm được công bố rõ.
- [ ] Runtime/isolation/cleanup đạt theo profile được chọn; attestation còn hiệu lực và source/manifest không trôi sau preview.
- [ ] Smoke thực có raw/reward/usage/cost và budget riêng; uncertainty được xử lý trước khi mở rộng theo policy.
- [ ] Pilot thực có coverage 72 trial hoặc báo thiếu/provisional đúng thực tế; không trộn smoke/simulation hoặc dùng best-of-three.
- [ ] Report phân biệt kết quả task, phí lúc settle, billing correction và unknown; archive/source/receipt có thể đối chiếu.
- [x] Các mốc model giai đoạn trước chỉ hoàn tất bằng bằng chứng tương ứng; A/private/release giữ deferred khi chưa đủ đầu vào.

**Bắt đầu khi triển khai:** U0–U1 với template hiện có. Nếu đầu vào vẫn thiếu, kết thúc phần chuẩn bị bằng danh sách quyết định cần cung cấp và vị trí tiếp tục chính xác; giữ trạng thái chưa chạy model. Khi có đầu vào, ưu tiên U2–U4 rồi smoke thực trước pilot.
