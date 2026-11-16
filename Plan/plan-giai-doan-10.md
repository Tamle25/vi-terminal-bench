# Kế hoạch giai đoạn 10 — Nối agent terminal và chạy smoke benchmark đầu tiên

- Ngày lập: 13/11/2026, Asia/Saigon.
- Trạng thái cập nhật 13/11/2026: đã triển khai thiết kế/draft, kit review pending, agent/controller/worker HTTP có deadline/ledger compute revision và kiểm offline; 203/203 test Linux đạt. G10.1 đạt cho thiết kế, G10.2 kiểm offline nhưng backend thực chưa nghiệm thu, G10.3/G10.4 chưa đạt/chưa chạy. Không có API request mới hoặc ngân sách mới. Xem [readiness](../reports/stage10-readiness.md) và [kiểm định](../reports/terminal-agent-offline-validation.md).
- Kế thừa: [giai đoạn 9](plan-giai-doan-9.md), [readiness](../reports/stage9-readiness.md), [summary](../reports/stage9-summary.json) và [kết quả kết nối](../reports/provider-connectivity.md).
- Mục tiêu: hoàn thiện đường **instruction → model → terminal trong sandbox → artifact → verifier → reward**, với trajectory và chi phí từng request; chạy smoke khi đủ điều kiện.
- Phạm vi chính: phần W4–W5 còn mở của giai đoạn 9. Pilot 72 trial là bước sau smoke, không phải điều kiện phải hoàn thành trong giai đoạn này.

## 1. Điểm xuất phát và khoảng trống

| Thành phần | Bằng chứng đã có | Việc còn thiếu |
|---|---|---|
| Dataset B | Sáu task development, instruction EN/VI, oracle/verifier/controls | Review độc lập: 0/6; độ khó provisional, license task chờ chủ dự án chốt |
| Công cụ offline | 164/164 test Linux đạt, Python 3.12.16; snapshot công khai được kiểm bytes | Kiểm đường agent terminal và USD nhiều request thực |
| OpenAI | Một request thật với `gpt-5.4-mini-2026-03-17`, HTTP 200/completed | Client text chưa có vòng lặp terminal/tool, checkpoint và artifact mapping cho benchmark |
| Chi phí | Token estimate 0,0000705 USD; reservation 0,01 USD còn giữ | Chưa có invoice; chưa có pool USD dùng chung giữa connectivity và smoke |
| Runtime | Có catalog `native-wsl-v1` và `desktop-relay-v1` | Chưa chọn/attest profile cho model smoke; lịch sử WSL/Docker còn gián đoạn |
| Đánh giá model | Chưa có terminal smoke hoặc điểm benchmark | Một cấu hình agent hoàn chỉnh và run spec smoke đủ gate |

Giữ nguyên kết quả lịch sử. Không chạy lại connectivity để kiểm key, không xóa claim/DB của run cũ và không dùng SIM_USD làm tiền thực. Trần 2 USD trước đó được ghi cho đợt kiểm kết nối; kế hoạch này chưa chuyển phần chưa dùng thành ngân sách smoke/pilot.

## 2. Mốc nghiệm thu

| Mốc | Sản phẩm cụ thể | Điều kiện đạt |
|---|---|---|
| G10.1 — Thiết kế thực thi | Inventory, thiết kế agent, draft run spec và bộ hồ sơ review | Quyết định kỹ thuật rõ; mỗi trường chưa có bằng chứng ghi `missing_input` hoặc `unverified` |
| G10.2 — Agent và accounting | Adapter terminal, vòng lặp tool, ledger USD nhiều request và kiểm thử liên quan | Gate trước request, giới hạn được thực thi, timeout/crash không gửi trùng hoặc mất phí |
| G10.3 — Sẵn sàng smoke | Task accepted, runtime thực, cấu hình đóng băng và ngân sách scope hợp lệ | Gate ngay trước thực thi đạt; credential chỉ ở host API client |
| G10.4 — Smoke có kết quả | Tối đa hai trial EN/VI, raw artifact, reward, request/usage/cost và report | Đường terminal/verifier chạy thật; phân biệt reward với lỗi hạ tầng và uncertainty |

Nếu thiếu reviewer hoặc quyền chi cho smoke, vẫn hoàn thành phần thiết kế, implementation và kiểm offline không phụ thuộc các đầu vào đó. Không ghi G10.3/G10.4 đạt bằng mock hoặc tự điền review.

## 3. W0 — Kiểm đầu vào và giữ lịch sử

- [x] Đối chiếu task/prompt snapshot, source hash, test report, receipt và archive giai đoạn 9; không đọc key để lập inventory.
- [x] Kiểm trạng thái claim của connectivity theo đường read-only. Ghi reservation còn giữ 0,01 USD và invoice còn thiếu; không release hoặc nhập thành chi phí 0.
- [x] Phân biệt source/task bất biến với tài liệu trạng thái có thể cập nhật. Với tài liệu đã đổi hợp lệ, kiểm bản lịch sử bên trong archive theo hash gốc; không sửa report cũ hoặc báo lịch sử hỏng chỉ vì README được cập nhật.
- [x] Tách trạng thái `provider-connectivity`, `model-smoke` và `native-pilot`; một scope đạt không tự mở scope kế tiếp.
- [x] Tạo inventory giai đoạn 10: reviewer, task, model, agent/version, runtime/profile, account/pool, caps và bằng chứng cho từng trường.

**Bàn giao dự kiến:** `reports/stage10-input-state.json` và danh sách quyết định còn thiếu trong `reports/stage10-run-spec.md`.

## 4. W1 — Chốt thiết kế agent và draft smoke

### Lựa chọn kỹ thuật ban đầu

Ưu tiên một host agent tối thiểu, dùng model snapshot đã kết nối thành công và một terminal tool chạy trong container task. Kỹ sư có thể chốt các lựa chọn triển khai thông thường trong phạm vi được giao; chỉ cần lấy thêm thông tin khi quyết định phụ thuộc reviewer, môi trường vận hành hoặc ngân sách chưa được cấp.

- [ ] Kiểm source/version Harbor và adapter hiện có, đối chiếu [hợp đồng executor](../docs/model-executor-contract.md). Chọn tái sử dụng agent có sẵn nếu đáp ứng gate/accounting/isolation; nếu không, triển khai host loop tối thiểu và ghi lý do.
- [x] Khi triển khai OpenAI/tool calling, xác minh schema, model compatibility, giá và retry từ tài liệu chính thức tại thời điểm thực hiện; ghi nguồn/ngày. Thành công của client text không chứng minh tool binding đã đúng.
- [x] Đóng băng agent ID/version/source, system prompt, tool schema, model/provider/API surface, reasoning, lịch sử hội thoại, quy tắc kết thúc và mapping artifact.
- [x] Chọn rõ điểm nối vào executor. Nếu schema hiện tại yêu cầu hai profile pilot, tạo schema smoke có version cho một profile; không điền cấu hình so sánh giả hoặc nới guard model cũ bằng đổi nhãn.
- [x] Phân tách registry adapter thực với fixture; config không được import module tùy ý hoặc tự khai `ready=true` để bật dispatch.

### Thiết kế smoke đề xuất

| Trường | Đề xuất để triển khai và kiểm |
|---|---|
| Scope | `model-smoke`, run ID mới, độc lập connectivity |
| Task ưu tiên | `b001-vn-invoice`; chỉ chạy sau acceptance đúng version/payload/prompt |
| Trial | Một cấu hình × cùng task × EN/VI × một lần = **2 planned trial** |
| Nếu task chưa được accepted | Giữ pending; không đổi task chỉ để có reward tốt hơn |
| Lịch sử | Container và hội thoại sạch cho từng trial; không truyền kết quả giữa EN/VI |
| Concurrency | 1 |
| Retry ban đầu | 0 retry tự động; mọi thay đổi cần policy/plan mới, không retry lời giải sai |
| Giới hạn sau triển khai draft | Tối đa 4 model request/trial và 1.024 output token/request; dự phòng toàn bộ model input maximum cho từng request; chưa mở dispatch |
| Giới hạn cần chốt cùng runtime | Tổng thời gian trial, timeout lệnh, input/context token, output bytes, CPU/RAM/disk, compute cap |

Hai trial dùng cùng policy và giới hạn tài nguyên; chỉ instruction EN/VI khác nhau. Đây là smoke đường chạy, chưa đủ repeat hoặc coverage để công bố chênh lệch năng lực EN–VI. Các giới hạn đề xuất là draft, không phải cấu hình đã kiểm hoặc quyền chi tiền.

**Bàn giao dự kiến:** `docs/terminal-agent-design.md`, `configs/stage10-smoke.draft.json` và `reports/stage10-run-spec.md`. File draft không được chạy thật.

## 5. W2 — Chuẩn bị và thu review độc lập

- [x] Chuẩn bị gói cho B001: instruction EN/VI, task version/payload hash và biểu mẫu từ [review template](../configs/review-records.stage5.template.json).
- [x] Bố trí tài liệu theo [review guide](../docs/review-guide.md): reviewer đọc instruction và giải độc lập trước khi xem oracle/expected; không đưa lời giải vào gói mở đầu.
- [ ] Reviewer là kỹ sư Việt Nam khác tác giả. Thu danh tính, ngày, thời gian giải thực, kiểm EN/VI, trường hợp biên, nhận xét grader và quyết định thật.
- [ ] Acceptance phải gắn đúng task version, payload và hai prompt hash. AI kiểm code, oracle pass hoặc fixture signoff không thay acceptance này.
- [ ] Nếu `changes_requested`, sửa đúng vấn đề, version hóa phần hợp đồng thay đổi, kiểm lại và review phần bị ảnh hưởng trước smoke; snapshot cũ giữ nguyên.
- [x] Chưa có reviewer thì bàn giao hồ sơ pending và tiếp tục W3–W5 phần kỹ thuật. Không tự ký nhận hoặc đổi manifest thành reviewed.

**Bàn giao dự kiến:** hồ sơ pending/record thật dưới `reports/reviews/`; report ghi rõ số task accepted. Một task accepted đủ cho smoke của task đó; pilot vẫn cần 6/6.

## 6. W3 — Vòng lặp model–terminal và artifact

- [x] Host gửi instruction cùng tool schema, nhận tool call và validate tên/arguments trước thực thi. Không thực thi text tự do ngoài giao thức tool đã chốt.
- [ ] Thực thi lệnh qua controller vào đúng container/run/workdir; không chuyển command từ model sang shell host. Cố định identity container, env, locale và encoding theo task.
- [ ] Trả stdout/stderr, exit code, timeout và phần bị cắt theo giới hạn byte đã chốt; giữ Unicode hợp lệ và metadata truncation. Tính cả tool output vào context/budget cho request sau.
- [x] Xử lý nhiều tool call theo policy đã đóng băng; chạy tuần tự cho smoke, không phát sinh concurrency ẩn.
- [x] Dừng khi model kết thúc, đạt cap request/context/time hoặc runtime/gate không còn hợp lệ. Phân loại agent failure, provider failure và infrastructure failure.
- [x] Lưu trajectory có thứ tự: request identity, tool call ID, command, kết quả, thời điểm, usage và trạng thái kết thúc; redaction trước khi ghi artifact công khai.
- [ ] Thu artifact bằng cơ chế có kiểm path/symlink; giữ bytes/tên Unicode trên filesystem Linux. Verifier offline chạy sau khi agent kết thúc, không chia sẻ expected/oracle cho agent.
- [x] Tách reward verifier, stop reason và độ đầy đủ của artifact. Model kết thúc bằng lời nói không được tự coi là giải đúng task.

**Bàn giao:** adapter/host loop có version, tool contract, trajectory schema và kiểm chứng transfer/verifier.

## 7. W4 — Accounting USD nhiều request và recovery

- [x] Tái sử dụng thiết kế reserve/claim/receipt đã kiểm; thêm schema USD có version cho run/trial/attempt/request. Không migrate archive fixture hoặc sửa ledger connectivity tại chỗ.
- [ ] Tạo pool/account reference cục bộ rõ ràng, map credential selector thật. Provider project ID chưa xác minh được ghi là chưa xác minh, không tự điền ID giả.
- [ ] Nhập exposure connectivity bằng record liên kết receipt/ledger gốc, chống nhập trùng. Không cộng reservation và token estimate thành hai khoản phí độc lập.
- [ ] Chốt cap inference, compute và tổng smoke theo scope được phép. Nếu quyền ngân sách hiện có chưa bao phủ smoke, hoàn thiện cấu hình/ước tính review được trước khi yêu cầu quyết định bổ sung; không hỏi lại phần đã được cấp.
- [x] Tính reservation từ giá được xác minh, token/context bound và số request. Context của request sau bao gồm lịch sử và output tool; không nhân đơn giá prompt đầu tiên cho cả vòng lặp.
- [x] Kiểm cap pool/run/trial trước từng request, claim bền vững rồi mới cấp credential và dispatch. Không gửi request khi không đủ reservation hoặc usage/context không có bound đáng tin cậy.
- [x] Ghi request ID, model/tier, input/cache/output/reasoning usage và error theo response thực. Tắt retry ngầm; mọi request có thể billable phải có record.
- [x] Timeout/crash/mất receipt giữ uncertainty và exposure. Không reset DB, resend hoặc tiếp tục partial trial khi chưa có checkpoint/accounting đủ căn cứ.
- [x] Nếu hỗ trợ resume, lưu checkpoint hội thoại/tool/artifact và chứng minh bước tiếp theo không gửi lại request hoặc thực thi lại command đã có hiệu lực. Nếu chưa hỗ trợ, khai báo dừng điều tra thủ công.
- [x] Tách token-price estimate, authoritative receipt/invoice và reservation. Correction dùng revision/overlay, không sửa raw hoặc cộng toàn bộ revision thành phí mới.

**Bàn giao:** schema/state mới, mapping receipt/cost, budget report và recovery runbook cho đúng khả năng thực tế của binding.

## 8. W5 — Runtime và kiểm định trước smoke

- [ ] Chọn profile thực từ [runtime catalog](../configs/runtime-profiles.json) dựa trên kiểm tra read-only và quyền vận hành hiện có. Không tự restart/prune workload chung hoặc đổi Docker root/endpoint để vượt lỗi.
- [ ] Kiểm engine Linux, user/endpoint, resources, timeout và lifecycle. Agent sandbox không có key, `.env`, oracle/test kín hoặc Docker control socket; host giữ API credential, verifier network `none`.
- [ ] Giới hạn mạng task theo nhu cầu đã ghi; model/tool output không tự mở thêm egress hoặc quyền host. Không cấp key cho container chỉ để đơn giản hóa vòng lặp.
- [ ] Kiểm filesystem Linux, case-distinct và NFC/NFD khi build/copy/transfer. Capture attestation mới gắn run/snapshot/profile, concurrency 1; kiểm lại khi hết hạn.
- [x] Kiểm offline các rủi ro của đường mới: gate fail tạo 0 request, cap khi context tăng, claim trùng, crash sau submit/receipt/tool, drift giữa vòng lặp, secret redaction và path/artifact isolation.
- [ ] Dùng response fixture và container command thử không gọi model để kiểm tích hợp host–terminal–artifact–verifier. Gắn nhãn offline, không tính là benchmark model.
- [x] Chạy regression thích hợp trên native Linux, kiểm hash input trước/sau và loại `.env` khỏi snapshot/archive. Không thêm simulation lớn chỉ để tăng test count; không đặt mục tiêu số test cố định.

**Điều kiện G10.3:** acceptance task + effective config/provenance + runtime attestation + binding/accounting + quyền chi/caps cùng đạt ngay trước dispatch. Gate không được chỉ đọc một JSON tự khai đã pass.

## 9. W6 — Thực thi smoke và bàn giao

- [ ] Đóng băng manifest model-smoke với hai planned trial ID, snapshot, instruction hash, source, model/agent/runtime/tools/limits và caps thực; lưu thứ tự EN/VI trước khi chạy.
- [ ] Chạy trial thứ nhất, thu artifact/reward/request/cost/cleanup; kiểm state trước trial thứ hai. Nếu có uncertainty hoặc lỗi isolation/accounting, dừng phần chưa gửi.
- [ ] Chạy trial thứ hai khi gate còn đạt; giữ history/container độc lập. Không thay prompt, tăng giới hạn hoặc chọn lại task sau khi thấy reward.
- [ ] Verifier reward 0 do giải sai vẫn là quan sát hợp lệ nếu hạ tầng chạy đúng. Nếu không có trajectory terminal thực hoặc verifier/artifact hỏng, không ghi smoke kỹ thuật đạt.
- [ ] Báo riêng: tính hợp lệ đường thực thi, mức hoàn thành hai trial, reward của agent và độ rõ của billing. Hai reward không tạo điểm pilot hoặc kết luận EN–VI.
- [ ] Lưu mọi request/attempt kể cả lỗi; raw → normalized → report phải đối chiếu được. Estimate chưa có invoice vẫn ghi provisional, không đổi thành authoritative cost.
- [ ] Archive source/config/trajectory/artifact/receipt trên filesystem Linux, kiểm checksum và restore; backup ledger đã redaction/kiểm không chứa secret.
- [x] Cập nhật readiness, kế hoạch tổng thể và liên kết README sau khi có bằng chứng mới. Các tài liệu lịch sử giữ đúng phiên bản trong archive; không sửa summary cũ để khớp source mới.

**Artifact dự kiến:** `reports/terminal-model-smoke.md`, `reports/stage10-readiness.md`, `reports/stage10-summary.json`, manifest/raw/normalized/provenance, ledger và archive theo run ID. Các đường dẫn này là sản phẩm cần tạo khi thực hiện, chưa phải evidence đã tồn tại.

## 10. Thứ tự và điểm dừng

```text
W0 inventory → W1 thiết kế/draft → W3 agent + W4 accounting → W5 kiểm định
                   └→ W2 review độc lập ───────────────────────────────┤
                       quyền chi/caps + runtime thực ─────────────────┤
                                                                    └→ W6 smoke
```

Các nhánh có thể tiến hành độc lập; sơ đồ không yêu cầu dùng nhiều agent. Ưu tiên tái sử dụng hạ tầng hiện có và làm đường smoke nhỏ nhất đủ bằng chứng trước khi mở rộng.

| Tình huống | Tiếp tục được | Phần chờ |
|---|---|---|
| Chưa có reviewer | Thiết kế, adapter, accounting, kiểm offline và hồ sơ review | Dispatch task benchmark |
| Chưa có cap/quyền chi smoke | Đóng băng draft, ước tính theo giá/context/request bound, kiểm offline | Request có tính phí của scope smoke |
| Docker/WSL không đạt | Code/kiểm unit không cần engine, chẩn đoán read-only | Attestation và trial cần sandbox |
| Có request uncertain | Lưu/reconcile evidence, kiểm state read-only | Request mới theo policy pool và resume trial |
| Reward 0, hạ tầng hợp lệ | Ghi kết quả, phân tích lỗi; trial kế tiếp theo plan nếu gate đạt | Không tự retry để cải thiện reward |

Không ấn định số ngày cho công việc phụ thuộc reviewer hoặc runtime chưa ổn định. Sau W1 mới ước lượng phần implementation theo lựa chọn agent thực; readiness phải nêu phần đã làm và điểm tiếp tục cụ thể nếu smoke chưa mở được.

## 11. Điều kiện chuyển sang pilot

Chỉ lập run pilot sau khi có smoke kỹ thuật hợp lệ, accounting/recovery đủ dùng, review 6/6 và hai cấu hình so sánh được đóng băng. Pilot giữ thiết kế **6 task × 2 instruction × 3 repeat × 2 cấu hình = 72 trial**, không tính connectivity hoặc smoke vào coverage. Ngân sách pilot cần scope/caps riêng; invoice/uncertainty còn lại xử lý theo policy pool trước dispatch.

Phần A vẫn theo [checklist Eval](../docs/eval-input-checklist.md). Giai đoạn này không mở thêm task, private split hoặc công bố dataset; license/attribution và review cần chốt trước phát hành.

## 12. Definition of Done

- [x] Evidence giai đoạn 9 được đối chiếu đúng phiên bản; không lộ credential hoặc làm mất claim/exposure cũ.
- [ ] Có agent/version/tools/effective config và source provenance thực; không dùng fixture signoff để mở model dispatch.
- [ ] Terminal loop thực thi đúng container, thu trajectory/artifact và chấm verifier riêng.
- [x] Ledger USD nhiều request kiểm cap/reservation/claim, giữ uncertainty và có recovery policy được kiểm.
- [ ] Task smoke có review độc lập đúng snapshot; runtime/isolation có attestation mới.
- [ ] Scope và ngân sách smoke hợp lệ trước request, không mặc định chi từ trần connectivity.
- [ ] Smoke có đủ evidence cho từng trial đã chạy; reward, lỗi hạ tầng, cost estimate và invoice được báo riêng.
- [x] Có readiness/summary/archive kiểm restore; nếu chưa đủ điều kiện chạy, ghi rõ mốc chưa đạt thay vì đánh dấu hoàn thành toàn giai đoạn.

**Bước đầu khi được yêu cầu thực hiện:** W0–W1 và chuẩn bị hồ sơ W2, sau đó triển khai W3–W5 phần không phụ thuộc reviewer/ngân sách. Không gửi lại request connectivity.

## 13. Nhật ký triển khai và việc còn mở

Ngày 13/11/2026: đã kiểm 309 đường dẫn lịch sử, source/archive giai đoạn 9 và DB connectivity read-only. Thiết kế, run spec và schema smoke một cấu hình đã có; source Harbor agent cài đặt chưa được kiểm, giữ lựa chọn host loop độc lập và guard cũ. Người dùng xác nhận chưa có reviewer; đã bàn giao kit instruction EN/VI + CSV gốc + pending record, không đáp án.

Đã viết loop strict tool calling, manual history, Docker exec/capture/transfer policy, verifier riêng, controller lifecycle, worker HTTP có deadline ở parent và ledger nano-USD 1.1 có request/compute revision. 39 test mới cùng hồi quy cuối đạt 203/203 trên bản sao Linux, 204 input công khai; integration hai fixture/bốn response giả/hai probe cố định, transfer và grader B001 thật nhận reward 0/0 như dự kiến. Checkpoint 197 test/source cũ giữ riêng để đối chiếu. Không dùng kết quả này làm bằng chứng container hoặc điểm model.

Draft giảm giới hạn request từ tám xuống bốn/trial vì reservation thận trọng 0,208608 USD/request, tổng tám request là 1,668864 USD inference. Pool/caps/compute/authorization thật vẫn null; chưa chi thêm. W0 và chuẩn bị W1/W2 đã bàn giao; W3–W5 đạt phần implementation/kiểm offline, chưa hoàn thành thực thi container. W2 còn cần người review thật, W6 chưa chạy.

Docker socket/WSL integration hiện không hoạt động ở hai lần probe; không restart/prune/switch endpoint. Controller/worker/compute đã có code và kiểm offline, còn cần kiểm backend thật và quote/persistent ledger path. Khi có runtime, ưu tiên container fixture, sau đó acceptance/authorization/attestation trước model smoke. Chưa đánh dấu toàn bộ các checkbox nghiệm thu bên trên vì các mục đó bao gồm bằng chứng thực còn thiếu.
