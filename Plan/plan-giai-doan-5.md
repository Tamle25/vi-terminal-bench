# Kế hoạch giai đoạn 5 — Nối executor thực, hoàn tất review và chạy pilot có điều kiện

- Ngày lập: 12/11/2026.
- Trạng thái cập nhật 12/11/2026: G5.1–G5.2 offline đã đạt; G5.3–G5.5 chờ đầu vào và kiểm định thực. G4.3–G4.5 vẫn mở.
- Kế thừa: [giai đoạn 4](plan-giai-doan-4.md), [readiness hiện tại](../reports/stage4-readiness.md), [tổng hợp bằng chứng](../reports/stage4-summary.json).
- Mục tiêu gần nhất: chuẩn bị đường thực thi model có kiểm soát, phân biệt phần có thể làm offline với phần cần reviewer, cấu hình và provider thực.
- Mục tiêu có điều kiện: hoàn tất các mục G4.3–G4.5 còn mở bằng smoke và native pilot B thật; không coi việc tạo kế hoạch mới là hoàn tất những mục đó.

**Kết quả đợt triển khai:** 102/102 test trên Linux/WSL đạt, 0 skip. Đường CLI mới được kiểm bằng hai trial fixture, ba attempt/năm request, dừng/resume qua ba tiến trình và restore DB. Đã nối gate trước từng request, giữ external cost uncertainty và phân tách smoke/pilot/simulation. Không gọi model/API thật, không tự accepted review hoặc chọn profile/ngân sách. Xem [readiness giai đoạn 5](../reports/stage5-readiness.md), [kiểm định executor](../reports/model-executor-offline-validation.md) và [hợp đồng](../docs/model-executor-contract.md).

Phạm vi đạt là hợp đồng và đường orchestration offline. Chưa có binding provider thực, enforcement API/isolation, ledger chung provider account hoặc recovery tự động cho mọi partial multi-request. Những mục cần agent/reviewer/runtime thực tiếp tục để mở bên dưới.

## 1. Điểm xuất phát

Đã có sáu task B development với instruction EN/VI. Bằng chứng trước đó gồm 18 oracle đạt, sáu nop nhận reward 0 và 125 controls. Giai đoạn 4 đạt 70/70 test Linux/WSL, kiểm định 72 trial mô phỏng qua 74 fake dispatch, hai retry và dừng/resume qua ba tiến trình. Task, prompt và năm archive lịch sử được bảo toàn.

Đây là bằng chứng kỹ thuật của dataset và harness. Chưa có kết quả model thật, review độc lập vẫn 0/6, độ khó provisional. Gate hiện kiểm tra tính nhất quán dữ liệu; executor model chưa triển khai. Chính sách network/socket trong JSON chưa chứng minh cách ly thực tế của một agent thật.

Các đầu vào người dùng đã xác nhận chưa có tiếp tục được ghi nhận là thiếu. Không hỏi lại chỉ để khởi động công việc offline; không tự chọn model, mua API credit, đặt giá hoặc điền reviewer. Đợt này không tăng số task hay chạy thêm một bộ simulation tương tự để thay thế những đầu vào đó.

## 2. Mốc và phạm vi nghiệm thu

| Mốc | Sản phẩm | Điều kiện nghiệm thu |
|---|---|---|
| G5.1 — Handoff và hợp đồng executor | Danh mục đầu vào, review record template, hợp đồng adapter/executor và scope smoke/pilot | Có công việc offline thực hiện được, không phụ thuộc API; gate thiếu đầu vào vẫn chặn dispatch |
| G5.2 — Đường thực thi offline | Orchestrator, interface adapter, provenance và ledger dùng chung được kiểm tra bằng fixture | Không gọi model, không đọc secret; kiểm tra đúng đường gọi dự kiến dùng cho executor thật |
| G5.3 — Cấu hình/runtime/review thực | Hai cấu hình, mapping đã kiểm, runtime và review accepted theo snapshot | Có bằng chứng từ agent/runtime và reviewer thực; đáp ứng phần G4.3 còn mở |
| G5.4 — Smoke thực | 1–2 trial riêng scope, budget và artifact | Xác nhận auth, tools, verifier, usage/cost, cleanup; đáp ứng G4.4 |
| G5.5 — Native pilot thực | 72 trial B cùng raw, normalized, ledger và báo cáo | Coverage và trạng thái thiếu minh bạch; đáp ứng G4.5 nếu đủ điều kiện nghiệm thu |

Nếu vẫn thiếu cấu hình/reviewer/ngân sách, điểm kết thúc của đợt triển khai là G5.1–G5.2 cùng báo cáo missing/deferred rõ từng mục. Không gọi adapter fixture là adapter thật đã kiểm định hoặc đánh dấu hoàn tất toàn bộ giai đoạn.

## 3. S0 — Bảo toàn bằng chứng và chốt hợp đồng bàn giao

- [x] Kiểm tra snapshot sáu task/prompt, năm archive cũ và archive simulation theo checksum đã ghi. Dùng output mới; giữ nguyên các report stage4.
- [x] Lập `reports/stage5-input-state.json` với thời điểm, run/snapshot/scope, trạng thái có kiểu và nguồn bằng chứng.
- [x] Lập danh sách quyết định còn thiếu theo đúng template hiện có: hai agent/model/version, provider/endpoint, prompt, effort, tools/kwargs, giới hạn token/turn/time, API architecture, credential mechanism, runtime và ngân sách.
- [x] Ghi riêng thiếu đầu vào người dùng, thiếu kiểm định kỹ thuật và phần không thuộc phạm vi. Không gộp thành một câu “cần xác nhận”.
- [x] Bàn giao review record mẫu còn trống cùng hash task/prompt hiện tại. Mẫu phải được đánh dấu chưa phải review thực và không được importer chấp nhận như record hoàn chỉnh.
- [x] Liên kết public/reference bundle, checksum và thứ tự mở theo [review guide](../docs/review-guide.md). Chưa gửi ra ngoài, upload hoặc công bố gói reference.

**Nghiệm thu:** chủ dự án biết cần giao ai quyết định gì; mọi trường chưa được cung cấp vẫn là null/pending. Không chạy lại toàn bộ oracle/control chỉ để lập inventory.

## 4. S1 — Hợp đồng executor và scope smoke/pilot

Kế thừa [schema trạng thái](../docs/pilot-state-schema.md), [mapping profile](../docs/model-profile-mapping.md) và [runner simulation](../docs/pilot-runner.md). Runner simulation tiếp tục có namespace riêng; không bật model bằng cách bỏ guard `--mode model` hiện tại.

- [x] Thiết kế entry point riêng cho model execution, mặc định chỉ validate/preview. Dispatch thật chỉ tồn tại khi có adapter đã chọn và bằng chứng cần thiết.
- [x] Xác định interface adapter: validate profile, build effective configuration, collect provenance, dispatch attempt, collect usage/artifacts và reconcile request nếu provider hỗ trợ.
- [x] Tách phần scheduler/ledger dùng chung khỏi fake provider khi việc tái sử dụng giúp giữ một đường logic. Giữ tương thích với bằng chứng simulation đã có; nếu thay schema phải có version/migration rõ ràng.
- [x] Định nghĩa capability của adapter theo từng provider: usage, pricing, timeout, cancellation, lookup, idempotency và error taxonomy. Không giả định mọi provider đều hỗ trợ những khả năng này.
- [x] Gắn provenance với adapter/version/source revision, runtime/config fingerprint, run/snapshot/scope và artifact do executor thu. Một file tự khai `kind=agent-verified` không tự chứng minh agent thực sự đã dùng cấu hình đó.
- [x] Thiết kế vòng đời secret: chỉ đọc ở đường dispatch thật sau các kiểm tra phù hợp; không truyền giá trị vào manifest, command log hoặc report. Offline path không cần secret.

### Phân biệt smoke và pilot

Gate hiện tại dành cho native pilot 72 trial. Cần bổ sung hợp đồng scope trước khi dùng cho smoke, thay vì nới điều kiện pilot để smoke đi qua.

| Scope | Trial và review | Ngân sách | Điểm tổng hợp |
|---|---|---|---|
| `model-smoke` | Danh sách con 1–2 trial rõ ràng, task được review đúng snapshot | Ledger và trần smoke riêng | Không nhập vào điểm pilot |
| `native-pilot` | 6 task × 2 ngôn ngữ × 3 repeat × 2 cấu hình = 72; review đủ 6/6 | Trần inference/compute của pilot | Tính theo giao thức đã chốt |
| `simulation` | Fixture, định danh và currency giả lập | SIM_USD | Chỉ kiểm tra pipeline |

- [x] Schema scope quy định chính xác planned trial, cấu hình, ngôn ngữ, repeat, attempt routing và điều kiện review; không cho thiếu nguyên cấu hình mà vẫn báo coverage đầy đủ.
- [ ] Nếu ledger smoke/pilot tách riêng, vẫn kiểm tổng chi tiêu và request uncertain khi dùng chung ngân sách/provider account.
- [x] Mỗi manifest có run ID mới, task snapshot và expected/effective fingerprints; lập trước dispatch. Không đổi loại run bằng cách sửa một trường trong ledger đã chạy.

**Bàn giao dự kiến:** `docs/model-executor-contract.md`, schema scope và fixture minh họa có nhãn simulation. Chưa tạo cấu hình model giả để gọi đây là G5.3.

## 5. S2 — Orchestrator, gate và ledger trên cùng đường thực thi

Đây là công việc có thể triển khai offline trước khi có provider cụ thể.

- [x] Nối orchestrator với readiness gate ngay trước dispatch, không chỉ khi tạo preview. Có kiểm tra lại snapshot/config, review, runtime validity, scope và ngân sách tại thời điểm thực thi.
- [x] Từ chối input simulation, oracle/nop hoặc attestation giả trên đường model. Giữ guard validation-only của runner oracle/nop.
- [x] Thu cấu hình hiệu lực từ adapter thay vì chỉ copy expected config sang observed. Kiểm tra prompt content hash, tools/kwargs, resource, network và concurrency.
- [x] Ghi reservation bền vững trước gửi request; giữ attempt/request identity, lease và receipt. Ngắt tiến trình giữa submit và persist không được tạo lý do tự gửi lại.
- [x] Unknown receipt/usage/cost giữ uncertain; chỉ reconcile bằng cơ chế có thật của provider. Không dùng “lookup không thấy” làm bằng chứng chắc chắn request chưa nhận hoặc chưa charge.
- [x] Kiểm soát ngân sách ở mức đủ gần lời gọi provider. Nếu một agent trial tạo nhiều request, adapter phải theo dõi từng request hoặc có upper bound reservation đã chứng minh từ giới hạn token/turn/tool; không chỉ kiểm một lần khi bắt đầu trial dài.
- [x] Khi phí vượt estimate/cap: lưu đúng phí quan sát, chặn dispatch mới và báo coverage thiếu. Không cắt số liệu về cap hoặc hứa trần cứng với phí chưa được provider xác nhận.
- [x] Retry chỉ cho lỗi đủ bằng chứng theo giao thức, tối đa hai retry bổ sung. Không retry lời giải sai hoặc agent failure để đổi reward.
- [x] Resume chỉ cùng snapshot, profile, adapter contract và budget đã đóng băng. Runtime observation mới có thể thay timestamp/socket tạm, nhưng stable runtime profile phải khớp.
- [x] Xuất raw → normalized → coverage/aggregate qua adapter import phù hợp; chưa coi raw của một provider mới là tương thích với importer Harbor hiện có nếu chưa đối chiếu.

### Kiểm định cần bổ sung

- [x] Gate fail tại thời điểm dispatch tạo đúng 0 lời gọi adapter/provider, kể cả preview trước đó đã pass.
- [x] Attestation hết hạn, snapshot/prompt đổi sau preview, wrong scope và missing configuration đều bị phát hiện.
- [x] Crash sau reserve, sau submit và sau receipt được kiểm qua entry point orchestrator dự kiến dùng thật, không chỉ qua helper độc lập.
- [x] Double-start không tạo hai chủ sở hữu cùng attempt; uncertain giữ reservation và chặn dispatch mới.
- [x] Budget cạn giữa các request trong một trial; retry vẫn giữ chi phí; request lỗi nhưng billable không bị ép về 0.
- [x] Smoke không lọt vào pilot score; simulation không sinh model provenance; adapter chưa hỗ trợ capability phải báo rõ.

Chỉ thêm test cho hành vi mới và rủi ro chưa được chứng minh. Dùng lại 70 test sẵn có làm regression khi thay code chung; không chạy lặp 72 trial simulation nếu thay đổi không tác động ledger/scheduler.

**Bàn giao dự kiến:** report kiểm định executor offline có platform, test count thực tế, giới hạn và 0 model calls. Không đặt trước số test phải đạt rồi viết kết quả theo con số đó.

## 6. S3 — Review độc lập và cấu hình agent thực

Nhánh này chỉ tiến triển khi có người review và quyết định cấu hình thực. Các công việc S1–S2 không cần đợi nhánh này.

### Review sáu task

- [ ] Chủ dự án chỉ định kỹ sư Việt Nam khác tác giả; reviewer đọc instruction và giải trước khi mở đáp án/reference.
- [ ] Thu thời gian giải thực đo, nhận xét ràng buộc EN/VI, verifier/expected/controls, artifact và quyết định theo hash.
- [ ] Validate record, đối chiếu hash và import bằng công cụ đã có; lưu nguồn record cùng backup. Không lấy oracle pass làm accepted.
- [ ] Nếu có changes requested, sửa đúng lỗi, tăng version khi thay hợp đồng và kiểm định lại phạm vi ảnh hưởng; cập nhật cả EN/VI khi cần.
- [ ] Giữ độ khó provisional cho tới khi có thời gian giải và bằng chứng đủ. Chỉ ghi 6/6 accepted khi có đủ record người thật cho snapshot pilot.

### Hai cấu hình và adapter cụ thể

- [ ] Nhận hai cấu hình theo [template](../configs/model-pilot.template.json). Hai cấu hình phải so sánh rõ được; nếu chỉ có một, báo thiếu cấu hình thay vì gọi run đó là pilot 72 trial hoàn chỉnh.
- [ ] Khóa version agent, Harbor, dependency và system prompt; đọc source/tài liệu chính thức của đúng adapter khi triển khai. Nếu cần đổi pin hiện tại, ghi lý do và kiểm tra tương thích liên quan.
- [ ] Triển khai mapping/kwargs allowlist của adapter đã chọn. Trường agent không hỗ trợ phải bị từ chối hoặc khai báo không áp dụng có cơ sở, không âm thầm bỏ qua.
- [ ] Thu effective configuration từ khởi tạo agent và so expected/effective. Kiểm tra đường gọi tools, workspace, resource limits, timeout và cách thu usage/cost.
- [ ] Xác minh giá provider hiện hành khi model được chọn, lưu nguồn/ngày/currency/unit và cách tính token/cache/tool fees có liên quan. Không đưa giá fixture SIM_USD vào ledger thật.
- [ ] Ghi rõ cái gì đã kiểm offline, cái gì kiểm với agent thật chưa gọi model và cái gì chỉ chứng minh được sau smoke.

**Nghiệm thu:** G5.3 không pass chỉ vì đủ trường JSON. Phải có nguồn bằng chứng runtime/adapter thực và review tương ứng scope; profile preview vẫn không phải quyền tự dispatch.

## 7. S4 — Runtime, API architecture và cleanup thực tế

- [ ] Chọn rõ một profile trong [runtime catalog](../configs/runtime-profiles.json), bắt đầu concurrency 1. Không tự chuyển native sang relay/root khi default fail.
- [ ] Kiểm tra distro/user/endpoint thực sự tương ứng profile, filesystem Linux hỗ trợ case và NFC/NFD, CLI/engine hiện tại và giới hạn tài nguyên.
- [ ] Kiểm chứng agent không đọc expected/oracle/test kín hoặc Docker control socket. Verifier offline và tách biệt đúng thiết kế.
- [ ] Nếu agent gọi API từ host: xác nhận container task/verifier không cần model credentials. Nếu từ container: kiểm chứng egress và secret injection thực; một field allowlist không chứng minh network enforcement.
- [ ] Capture attestation mới đúng run/snapshot/profile trước dispatch; mặc định 300 giây, tối đa 900 giây theo hợp đồng hiện có. Run dài cần capture mới khi hết hiệu lực, không tăng TTL tùy ý để qua gate.
- [ ] Hết hạn evidence không làm mất kết quả request đã gửi: giữ receipt/cost, chặn request mới tới khi kiểm tra lại đạt. Endpoint tạm đổi chỉ hợp lệ khi stable profile và policy vẫn khớp.
- [ ] Kiểm định cleanup khi kết thúc bình thường, lỗi và hủy process: chỉ socket/process/container/temp do run sở hữu. Giữ raw/ledger phục vụ reconcile; không restart dịch vụ chung hoặc prune cache của workload khác.
- [ ] Nếu muốn tăng concurrency, kiểm tra giới hạn runtime, reservation đồng thời và smoke hạ tầng nhỏ trước; không suy runtime concurrency 2 từ test SQLite hai worker.

Nếu runtime chưa hoạt động, báo trạng thái kỹ thuật riêng. Workaround relay đã kiểm development không được mô tả là sửa triệt để integration mặc định.

## 8. S5 — Smoke model thật, có điều kiện

**Chỉ bắt đầu khi** cấu hình thực và phạm vi ngân sách đã có, task trong smoke được review, adapter/runtime phù hợp đã kiểm, manifest smoke đúng và gate scope smoke đạt. Không dùng fixture để thay bằng chứng thực.

- [ ] Lập run ID, scope `model-smoke`, 1–2 trial và budget smoke riêng. Khi có hai cấu hình, ưu tiên một trial mỗi cấu hình; ghi rõ các tổ hợp chưa được smoke.
- [ ] Tạo môi trường sạch, không kế thừa trajectory hoặc output simulation. Ghi effective config trước thực thi.
- [ ] Kiểm auth, model/provider ID, tool execution, reward, artifact transfer, timeout, usage/cost và cleanup. Reward 0 do giải sai không đồng nghĩa hạ tầng smoke hỏng.
- [ ] Đối chiếu model requests thực với ledger; request billable chưa xác định phải reconcile trước pilot. Nếu chưa thu được usage/cost thì giữ unknown, không kết luận miễn phí.
- [ ] Phân loại lỗi task/agent/profile/infra/provider và sửa đúng phạm vi. Không tự retry lỗi nhận dạng chưa đủ bằng chứng.
- [ ] Xuất `reports/model-smoke.md` và archive Linux theo run ID; ghi giới hạn smoke thay vì suy rộng toàn bộ pilot.

Nghiệm thu smoke dựa trên đường thực thi, provenance, chấm và accounting đúng; không yêu cầu chọn lại task cho tới khi model pass. Chỉ sau smoke đạt mới xem xét G5.5 trong budget đã có; không tự tăng ngân sách.

## 9. S6 — Native pilot B thật và phân tích

- [ ] Đóng băng sáu task đã review, hai cấu hình, EN/VI, ba repeat và manifest **72 trial**, chưa gồm smoke/retry.
- [ ] Ghi seed/thứ tự đã trộn; môi trường và lịch sử độc lập mỗi trial, ngân sách tương đương EN–VI trong từng cấu hình.
- [ ] Kiểm readiness trước dispatch, theo dõi lease/uncertain/cost/runtime; dừng phần chưa chạy khi điều kiện không còn đạt. Không hủy thông tin phí của request đang thực thi.
- [ ] Giữ tối đa ba attempt theo giao thức; coverage tính theo planned trial, không coi retry là repeat hoặc lấy best-of-three.
- [ ] Lưu provenance, raw/reference, normalized, ledger và bằng chứng config/runtime theo run. Đóng gói Linux để bảo toàn Unicode/case rồi kiểm checksum và restore.
- [ ] Tính score theo [giao thức](../docs/evaluation-protocol.md), macro theo task/skill và delta EN–VI; báo số trial hợp lệ/thiếu/uncertain cùng lỗi hạ tầng.
- [ ] CI theo family chỉ báo khi thiết kế đủ để ước lượng. Native-six hiện một family/skill nên giữ null và lý do; ba repeat không tạo thêm family độc lập.
- [ ] Lập taxonomy lỗi có ví dụ đã loại secret: encoding/Unicode, tìm kiếm, collation, số/ngày, CSV, instruction, công cụ và hạ tầng.
- [ ] Viết `reports/native-model-pilot.md`, giới hạn development set, ngày chạy, version, chi phí đã biết và chưa biết. Nếu run chưa đủ 72, báo pilot một phần, không đánh dấu coverage hoàn chỉnh.

Nếu phát hiện lỗi task làm mất tính hợp lệ của so sánh, tăng version, xác định trial bị ảnh hưởng ở cả EN/VI và chạy lại đối xứng khi có budget phù hợp. Không sửa verifier riêng một phía rồi giữ điểm cũ phía còn lại.

## 10. S7 — Phần A, tập kín và phát hành

- [ ] Phần A tiếp tục `missing_input` theo [checklist Eval](../docs/eval-input-checklist.md). Chỉ thêm sáu task A và 144 trial khi có snapshot, quyền dùng và cấu hình baseline có thể đối chiếu.
- [ ] Tách báo cáo A/B. Không gọi sáu task A là toàn bộ Terminal-Bench 4.0 hoặc dùng kết quả B để suy ra khoảng cách instruction A.
- [ ] Sáu task B hiện tại vẫn là development. Thiết kế private families theo [tài liệu tập kín](../docs/private-test-design.md) sau khi học từ lỗi pilot; không tạo thêm task để né review và adapter còn thiếu.
- [ ] License, hosting, test kín và phát hành là công việc có điều kiện riêng. Không upload hoặc publish từ việc thực hiện kế hoạch này.

## 11. Thứ tự và thời gian dự kiến

```text
S0 → S1 hợp đồng scope/executor → S2 nối đường offline ─────────────┐
S3 review + hai cấu hình → adapter cụ thể ──────────────────────────┤
S4 runtime/API/cleanup theo profile đã chọn ────────────────────────┤
                                                                 └→ S5 smoke → S6 pilot
S7 A/private/release: nhánh có điều kiện, không chặn S0–S2.
```

| Công việc | Ước lượng ngày làm việc | Phụ thuộc |
|---|---:|---|
| S0 và S1 | 1–2 | Không cần API hoặc reviewer để chuẩn bị hợp đồng |
| S2 và kiểm định đường thực thi offline | 2–3 | Hợp đồng S1; không cần paid run |
| Báo cáo bàn giao offline | 1 | Kết quả kiểm định thực tế |
| Review sáu task | Ước lượng sau khi có reviewer | Người được giao review và thời gian giải thực |
| Adapter/provider thực và S4 | Ước lượng sau khi chốt cấu hình | Agent, provider, runtime và kiến trúc API |
| Smoke và 72 trial pilot | Theo timeout, tài nguyên và budget thực | S3/S4 đạt và ngân sách theo scope |

Khoảng 4–6 ngày cho phần chuẩn bị/offline là ước lượng lập kế hoạch, không gồm chờ đầu vào hoặc cam kết số ngày để sửa mọi lỗi provider/runtime. Không quy đổi thành chi phí API khi chưa có model và giá xác minh.

## 12. Definition of Done và điểm dừng

- [x] Snapshot và bằng chứng lịch sử giữ nguyên; mọi report mới có run/scope/thời điểm và source rõ ràng.
- [x] Có danh mục quyết định còn thiếu và review template dùng được, không chứa acceptance giả.
- [x] Có hợp đồng scope smoke/pilot, adapter capability và đường orchestration được kiểm offline.
- [x] Gate được gọi trên đường dispatch, không chỉ ở preview; test thay đổi evidence sau preview vẫn chặn gọi provider.
- [x] Ledger/resume/uncertain/retry giữ đầy đủ attempt/cost; không giả định provider idempotency hoặc lookup authoritative.
- [x] Báo cáo nêu chính xác phần offline đạt, phần agent/runtime thực chưa kiểm và 0 model calls nếu chưa chạy thật.
- [ ] Khi có đầu vào: review, effective config, isolation, runtime và pricing được kiểm từ nguồn thực trước smoke.
- [ ] Chỉ khi chạy thật: có smoke/pilot report, raw archive, cost ledger và coverage tương ứng thực tế.
- [x] G4.3–G4.5 chỉ cập nhật hoàn tất theo bằng chứng thật; A/private/release giữ deferred nếu chưa đủ điều kiện.

**Bước đầu khi triển khai:** S0 và S1, sau đó nối S2 với fake adapter có nhãn rõ. Tiếp tục các phần độc lập trong khi chờ reviewer/model/budget; dừng đúng phần phụ thuộc khi chưa có dữ liệu thực, không lặp thêm simulation để tuyên bố đã có pilot model.
