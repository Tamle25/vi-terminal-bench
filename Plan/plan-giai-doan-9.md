# Kế hoạch giai đoạn 9 — Chốt run thực, kiểm kết nối provider và chạy benchmark smoke

- Ngày lập: 13/11/2026.
- Trạng thái cập nhật 13/11/2026: hoàn thành W0–W3 cho scope `provider-connectivity`; G9.1–G9.2 đạt trong scope đó. Một request thực HTTP 200, token cost ước tính 0,0000705 USD; 164/164 test Linux đạt. W4–W6 chưa hoàn tất. Xem [readiness](../reports/stage9-readiness.md), [run spec](../reports/stage9-run-spec.md) và [kết quả](../reports/provider-connectivity.md).
- Kế thừa: [giai đoạn 8](plan-giai-doan-8.md), [readiness hiện tại](../reports/stage8-readiness.md), [bằng chứng bàn giao](../reports/stage8-summary.json).
- Mục tiêu: chuyển từ credential loader đã kiểm offline sang một đường gọi provider thực có giới hạn, rồi nối agent terminal và chạy smoke benchmark trước pilot.
- Ưu tiên: chốt đầu vào thực và triển khai đúng binding được chọn. Tái sử dụng hạ tầng hiện có; không đặt mục tiêu mở rộng task, tăng test count hoặc thêm một run simulation 72 trial.

## 1. Điểm xuất phát

Đã có sáu task B development, EN/VI, verifier và harness offline. Giai đoạn 8 đạt **150/150 test Linux**, gồm loader theo process, redaction và source policy loại `.env` khỏi snapshot. Credential được lưu cục bộ, nhưng auth/model access/quota chưa được kiểm qua API.

Điểm xuất phát trước triển khai: provider SDK/agent binding thực chưa có. Hai cấu hình model, budget/account/pool và runtime chưa chốt; review độc lập **0/6**. Core model guard giữ nguyên, ledger fixture chỉ hỗ trợ SIM_USD. Sau triển khai đã có client text connectivity và ledger USD riêng cho đúng một run; agent terminal, shared USD pool và các mốc benchmark model vẫn chưa hoàn tất.

Giai đoạn này phân biệt ba mức bằng chứng: kết nối provider, agent terminal hoàn thành một smoke, và kết quả pilot 72 trial. Mỗi mức có scope/budget/artifact riêng; đạt mức trước không tự hoàn tất mức sau.

## 2. Mốc và điều kiện nghiệm thu

| Mốc | Sản phẩm | Điều kiện đạt |
|---|---|---|
| G9.1 — Run spec tối thiểu | Model và scope/budget cho bước thực đầu tiên | Có lựa chọn thực, account reference và giới hạn; không dùng placeholder |
| G9.2 — Kết nối provider thực | Một kiểm tra kết nối có giới hạn nếu cần | Đúng model, credential, request ID, usage và accounting; không tính là điểm benchmark |
| G9.3 — Agent terminal smoke | 1–2 trial benchmark thật | Task được review, agent/runtime/billing đã kiểm và gate smoke đạt |
| G9.4 — Native pilot B | 72 trial cùng raw/normalized/ledger/report | Hai cấu hình, review 6/6, coverage và chi phí đối chiếu được |

Kiểm tra kết nối G9.2 có thể làm trước review task vì không sử dụng task benchmark hoặc chấm năng lực. Nếu đi thẳng vào smoke thì phải đáp ứng đầy đủ điều kiện review/agent/runtime của G9.3. Không dùng bước kết nối để nới gate benchmark.

## 3. W0 — Chốt đầu vào tối thiểu trước khi viết binding

- [x] Đối chiếu snapshot task/prompt, source/report/archive và trạng thái credential theo bằng chứng giai đoạn 8, không đọc hoặc đưa key vào inventory.
- [x] Dùng lại [gói quyết định](../reports/stage7-decision-package.md), [template model](../configs/model-pilot.template.json) và [hướng dẫn credential](../docs/credential-loading.md).
- [x] Ghi quyết định mới: người dùng ủy quyền kỹ sư chọn model và cho phép kiểm tra với trần 2 USD. Chọn `gpt-5.4-mini-2026-03-17` từ tài liệu chính thức; account reference là nguồn project key cục bộ đã cung cấp, chưa xác minh provider project ID. Quyền này mở scope connectivity, chưa mở benchmark pilot.

| Đầu vào | Cần cho bước nào | Người cung cấp/chốt |
|---|---|---|
| Một model ID/provider cụ thể | Kết nối đầu tiên | Chủ dự án/đội Eval |
| Cap kiểm tra kết nối hoặc smoke, currency, account reference | Trước request thật | Chủ dự án |
| Agent/version, prompt/tools/limits và API architecture | Terminal smoke | Chủ dự án cùng kỹ sư triển khai |
| Runtime profile và tài nguyên | Terminal smoke | Người vận hành |
| Reviewer/task được giao | Smoke task được chọn; sau đó đủ sáu task cho pilot | Chủ dự án/reviewer |
| Cấu hình so sánh thứ hai và budget pilot | Pilot 72 trial | Chủ dự án/đội Eval |

Người phụ trách có thể cung cấp model/provider và caps trước; version/endpoint/kwargs tương thích sẽ được kỹ sư xác minh từ source/tài liệu chính thức sau lựa chọn đó. Không cần tự điền các thông số SDK chưa biết để bắt đầu trao đổi cấu hình.

**Bàn giao dự kiến:** `reports/stage9-run-spec.md` và inventory có trạng thái theo scope. Nếu đầu vào vẫn thiếu, chỉ hoàn tất phần chuẩn bị; G9.1 tiếp tục `missing_input`, chưa gửi request và chưa tạo binding giả để báo đã tiến triển model.

## 4. W1 — Định nghĩa scope và đóng băng run spec

| Scope | Điều kiện riêng | Dữ liệu đầu ra |
|---|---|---|
| `provider-connectivity` | Model/account/cap rõ, binding request và reservation đủ cơ sở; không cần task benchmark | Auth/model response, request/usage/cost hoặc lỗi có phân loại |
| `model-smoke` | Agent, task được review, runtime/isolation và cap smoke | Artifact task, verifier reward, trajectory và billing |
| `native-pilot` | Hai cấu hình, review 6/6, smoke đạt và budget pilot | 72 planned trial cùng coverage/score/ledger |

- [x] Nếu có connectivity check, định nghĩa manifest/schema riêng cho scope này. Không đưa một cấu hình vào template pilot vốn yêu cầu hai cấu hình rồi coi đó là pilot hợp lệ.
- [x] Đặt run ID mới, model/version/source, prompt/input, giới hạn request/token/time, cap và cơ chế cấp credential. Connectivity check ban đầu có số request được đóng băng nhỏ, không tự thử thêm model khi lỗi.
- [x] Giữ scope kết nối/smoke/pilot tách biệt khi aggregate; cùng account/pool vẫn phải tính tổng exposure và request uncertain.
- [x] Ghi rõ được phép thực thi scope nào. Quyền kiểm kết nối không tự mở smoke hoặc pilot ngoài budget đã có.
- [x] Manifest tự sinh khi chưa đủ quyết định tiếp tục là preview; presence của key hoặc một field `ready=true` không mở dispatch.

## 5. W2 — Provider binding và accounting cho request thực

Chỉ triển khai theo provider/model đã chọn. Dùng OpenAI credential đã có cho cấu hình OpenAI tương ứng; không mặc định cấu hình thứ hai cùng provider/account.

- [x] Đọc source/tài liệu chính thức của đúng SDK/agent/version; chọn API surface và dependency cần thiết cho đường đã chốt. Không lấy model trong ví dụ tài liệu làm model mặc định.
- [x] Lưu source snapshot/hash theo run mới; version hóa binding/schema thay đổi. Lịch sử phải được đối chiếu bằng source của đúng snapshot/archive, không sửa report cũ để khớp code mới.
- [x] Nối factory/registry kiểm soát trong code với credential loader và gate thực. Không bật model bằng đổi nhãn fixture hoặc xóa guard cũ.
- [x] Thu effective config và kiểm model/provider/endpoint/effort/prompt/tool/limits trước request.
- [x] Ghi intent và reservation trước dispatch; thu client/provider request ID, usage, response/error và raw reference. Không coi thiếu response ID là bằng chứng chưa nhận/chưa charge.
- [x] Kiểm retry ẩn của SDK/agent. Request có thể tính phí phải được trace/accounting; không để một lệnh client âm thầm vượt số request/cap của run spec.
- [x] Xác minh giá tại thời điểm chuẩn bị chạy khi đã có model; lưu nguồn/ngày/unit và cách tính usage/cache/tool fees liên quan. Không tự đặt giá hoặc dùng SIM_USD làm tiền thật.
- [x] Triển khai phần accounting tiền thực có version và đủ cho scope đang chạy. Ledger fixture hiện từ chối USD; giữ namespace, state và bằng chứng cũ độc lập.
- [x] Unknown cost giữ unknown/exposure; request lỗi cũng có thể billable. Không tự release vì timeout hoặc lookup không thấy; capability chưa có được ghi rõ.
- [ ] Giữ raw task và authoritative billing overlay khi có correction. Không cộng phí ban đầu và toàn bộ các revision như những request độc lập. Không áp dụng connectivity một request; còn mở cho terminal benchmark.
- [x] Chỉ cấp credential cho process/client cần nó sau gate, dùng output/error đã giới hạn. Không đưa `.env`, key hoặc Authorization vào log/source archive.

Kiểm offline tập trung vào đường mới: request/usage/error mapping, cap và retry, gate fail tạo 0 request, source/config drift và redaction. Tái sử dụng regression hiện có, chỉ chạy lại fixture integration khi thay đổi có ảnh hưởng. Không tạo thêm một bộ simulation lớn để thay request thực còn thiếu.

**Bàn giao:** binding/effective-config diff, source/version, mapping usage/receipt và report kiểm định. Mock pass chỉ xác nhận phần contract; auth/quota và response thực vẫn chờ W3.

## 6. W3 — Kiểm kết nối có giới hạn, nếu cần

**Điều kiện bắt đầu:** model và cap kiểm tra đã được cung cấp trong phạm vi cho phép; binding, reservation/accounting và credential path đủ điều kiện; manifest scope kết nối đã đóng băng và gate tương ứng đạt.

- [x] Gửi request tối thiểu theo run spec, không dùng task benchmark, oracle, reference hoặc dữ liệu kín. Không cần Docker sandbox nếu request này không thực thi terminal/tool.
- [x] Thu response hoặc lỗi phân loại, model/request ID, usage và chi phí đã biết/chưa biết. Không in credential hoặc raw headers nhạy cảm.
- [x] Auth/model-access/quota chỉ được báo theo bằng chứng thật quan sát được; không suy một response thành bảo đảm quota cho toàn pilot.
- [x] Nếu request lỗi, giữ attempt/receipt/exposure và điều tra trước khi gửi lại. Không tự đổi model, tăng cap hoặc thử hàng loạt key/config.
- [x] Viết `reports/provider-connectivity.md` và artifact theo run ID. Gắn nhãn đây là kiểm kết nối, không phải benchmark score hoặc terminal smoke.

Nếu agent binding có thể được kiểm an toàn bằng smoke trực tiếp và không cần bước kết nối riêng, ghi không áp dụng bước này với lý do rồi tuân thủ toàn bộ W4–W5. Không tạo một request phụ chỉ để tăng số liệu kiểm định.


**Kết quả thực thi W0–W3:** dùng client stdlib cố định thay SDK; source/manifest được đóng băng, ledger USD một run có claim/reservation trước request, không retry. HTTP 200/completed; 22 input + 12 output token, 0,0000705 USD token estimate; reservation 0,01 USD vẫn giữ đến khi đối soát invoice. Correction overlay cho raw task không áp dụng connectivity và còn mở cho terminal benchmark. Shared USD pool nhiều run chưa triển khai. Các tick W2 chỉ chứng nhận scope một request này.

## 7. W4 — Review, agent terminal và runtime

### Review và nguồn task

- [ ] Giao reviewer kỹ sư Việt Nam khác tác giả theo [hướng dẫn](../docs/review-guide.md); giải trước reference và ghi thời gian thực.
- [ ] Thu record thật gắn task version/payload và cả prompt EN/VI; dùng [template](../configs/review-records.stage5.template.json) hiện có. Oracle/control/fixture không tạo accepted.
- [ ] Giữ attribution `Codex-assisted`, độ khó provisional khi chưa đủ bằng chứng. Nếu đổi hợp đồng task, version hóa và kiểm định/review lại phần bị ảnh hưởng ở cả EN/VI.

### Agent và sandbox

- [ ] Chọn agent/version và mapping terminal tools theo [hợp đồng executor](../docs/model-executor-contract.md); một API client trả text chưa chứng minh agent terminal hoạt động.
- [ ] Kiểm command execution, workspace, artifact transfer và cách thu trajectory. Giữ môi trường/lịch sử trial độc lập.
- [ ] Người vận hành chọn runtime trong [catalog](../configs/runtime-profiles.json), bắt đầu concurrency 1. Không tự chuyển root/endpoint hoặc restart workload chung khi default fail.
- [ ] Kiểm CLI/engine/user/endpoint, filesystem Linux/case/NFC/NFD, resource/time limits, API egress và secret path thực.
- [ ] Agent không tiếp cận oracle/expected/test kín hoặc Docker control socket; verifier offline và không nhận credential API.
- [ ] Capture attestation mới theo run/snapshot/profile, kiểm lại khi hết hiệu lực; cleanup chỉ tài nguyên của run và giữ raw/ledger để reconcile.
- [ ] Partial multi-request thiếu checkpoint giữ uncertain. Chỉ tiếp tục khi có đủ bằng chứng request/agent state và gate hiện tại đạt; không tự chạy lại từ đầu như chưa phát sinh phí.

Default WSL còn lịch sử gián đoạn; relay development không thay thế preflight cho run model hiện tại. Bằng chứng connectivity cũng không thay kiểm tools/isolation/verifier.

## 8. W5 — Benchmark smoke 1–2 trial

- [ ] Chọn task đã accepted đúng snapshot, profile agent/model và cap smoke thực; lập scope `model-smoke` riêng với planned IDs và attempt routing.
- [ ] Kiểm gate config/review/runtime/budget ngay trước request; môi trường sạch và không kế thừa output từ fixture/connectivity check.
- [ ] Thu auth/model ID, tool execution, artifact, verifier reward, request/usage/cost và cleanup. Reward 0 do giải sai vẫn là kết quả task hợp lệ.
- [ ] Phân biệt task/agent/provider/infra failure, giữ mọi attempt/cost; chỉ retry khi có căn cứ theo giao thức, không đổi task tới khi pass.
- [ ] Reconcile uncertainty trước khi mở rộng theo policy của pool. Không tự thêm budget khi số dư chưa đủ.
- [ ] Viết report smoke và archive Linux có checksum/source/receipt; chỉ sau smoke đạt mới chuyển pilot trong scope/budget đã được cung cấp.

Một cấu hình đã chốt có thể đủ cho smoke riêng của cấu hình đó nếu schema scope hỗ trợ và được kiểm rõ. Nó không làm hoàn tất yêu cầu hai cấu hình của pilot so sánh.

## 9. W6 — Pilot 72 trial và báo cáo đầu tiên

- [ ] Hai cấu hình đã chốt/kiểm, review 6/6, smoke đạt, cap pilot/pool có cơ sở và không còn uncertainty chặn dispatch.
- [ ] Đóng băng **6 task × 2 instruction EN/VI × 3 repeat × 2 cấu hình = 72 trial**, chưa gồm connectivity/smoke/retry; ghi seed/thứ tự, snapshot và source/runtime contracts.
- [ ] Giữ budget EN–VI tương đương trong từng cấu hình, history độc lập mỗi trial; gate/reserve trước request và giữ mọi attempt.
- [ ] Tối đa hai retry bổ sung theo [giao thức](../docs/evaluation-protocol.md), không retry lời giải sai hoặc lấy best-of-three.
- [ ] Dừng phần chưa gửi khi cap/runtime/evidence không còn đạt; giữ kết quả/phí request đã gửi để reconcile.
- [ ] Xuất raw/normalized/provenance, ledger/overlay; đối chiếu reward, latest billing revision và delta. Kết quả task đã biết và billing chưa rõ được báo riêng.
- [ ] Báo valid/missing/infra/uncertain theo task/config/language/repeat. Pilot thiếu coverage hoặc còn infra unresolved được ghi là một phần/provisional.
- [ ] Tính macro/delta EN–VI trên điều kiện khớp. Một family/skill vẫn chưa đủ CI B; ba repeat không tạo family mới.
- [ ] Archive trên filesystem Linux, kiểm checksum/restore và ghi giới hạn resume/checkpoint. Viết `reports/native-model-pilot.md` chỉ bằng kết quả thực.

Phần A tiếp tục theo [checklist Eval](../docs/eval-input-checklist.md); private families và phát hành theo quyết định sau pilot. Không gọi subset A là toàn bộ Terminal-Bench hoặc dùng kết quả development B để suy thành năng lực tổng quát.

## 10. Thứ tự, thời gian và điểm dừng

```text
W0 đầu vào → W1 run spec → W2 binding/accounting → W3 connectivity nếu cần
                                           └─────────────────────────────┐
W4 review + agent/runtime ────────────────────────────────────────────────┤
                                                                       └→ W5 smoke → W6 pilot
```

| Công việc | Ước lượng lập kế hoạch | Phụ thuộc |
|---|---|---|
| W0–W1 chuẩn bị run spec | Khoảng 0,5–1 ngày kỹ thuật | Có thể ghi phần thiếu từ bằng chứng hiện có |
| Chốt model/caps/account/reviewer | Theo người phụ trách | Quyết định thực; không ấn định thay chủ dự án |
| W2 binding/accounting | Ước lượng sau khi chọn provider/agent/API surface | Đúng source/version và scope |
| W3 connectivity | Theo số request/timeout đã chốt | Budget/reservation và binding đạt |
| W4 agent/runtime/review | Ước lượng theo lựa chọn và lỗi thực | Người review, môi trường và quyền vận hành |
| W5–W6 | 1–2 smoke trial rồi 72 pilot trial theo tài nguyên thực | Gate, coverage review và ngân sách |

Không ước tính giá API trước khi có model và nguồn giá xác minh. Khi thiếu đầu vào, bàn giao `reports/stage9-readiness.md` cùng vị trí tiếp tục; giữ trạng thái chưa chạy. Không tạo client/API call chỉ để thử key đang có khi chưa có model và budget cho scope đó.

## 11. Definition of Done

- [x] Lịch sử task/source/report/archive giữ nguyên theo đúng snapshot; không có secret trong bằng chứng mới.
- [x] Có run spec thực với model, account, caps và scope; phần thiếu được ghi rõ, không tự điền placeholder thành cấu hình chạy. Account reference là nguồn key thực cục bộ; provider project ID chưa xác minh.
- [x] Binding/config/accounting được kiểm theo SDK/agent đã chọn; key presence không tự chứng minh auth/quota hoặc quyền chi tiền.
- [x] Connectivity nếu đã thực hiện có evidence/request/usage/cost riêng, không trộn vào benchmark score.
- [ ] Review, terminal tools, runtime/isolation/cleanup và attestation đạt trước smoke benchmark.
- [ ] Smoke có kết quả thực và billing rõ theo policy; pilot có đủ 72 trial hoặc báo phần thiếu đúng thực tế.
- [x] G8.2–G8.5 và các mốc model cũ chỉ cập nhật khi bằng chứng tương ứng đạt; A/private/release tiếp tục deferred khi thiếu đầu vào. Connectivity không hoàn tất các mốc terminal smoke/pilot cũ.

**Bước đầu khi triển khai:** W0–W1. Khi đã có model/cap/scope thực, ưu tiên binding cần cho lần thực thi nhỏ đầu tiên; review và chuẩn bị agent/runtime tiến hành theo phạm vi tương ứng. Nếu đầu vào vẫn thiếu, hoàn tất gói run còn thiếu và dừng nhánh phụ thuộc đó.
