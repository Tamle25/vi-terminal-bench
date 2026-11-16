# Kế hoạch giai đoạn 4 — Đóng điều kiện readiness và xây pilot runner có kiểm soát

- Ngày lập: 12/11/2026.
- Trạng thái cập nhật 12/11/2026: G4.1–G4.2 offline đã đạt; G4.3–G4.5 chờ đầu vào thực. Không đánh dấu hoàn tất pilot model.
- Kế thừa: [giai đoạn 3](plan-giai-doan-3.md), [readiness hiện tại](../reports/stage3-readiness.md), [model profile](../docs/model-run-profile.md).
- Mục tiêu gần nhất: biến các điều kiện runtime/review/profile/ngân sách thành dữ liệu và kiểm tra tự động; kiểm định runner bằng mô phỏng offline.
- Mục tiêu có điều kiện: chạy smoke model và native pilot 72 trial khi đã có đủ cấu hình, ngân sách, review và runtime phù hợp.

**Kết quả triển khai:** 70/70 test Linux/WSL đạt, 72 trial mô phỏng hoàn tất qua 74 fake dispatch và hai retry. Đã kiểm tra dừng/resume qua ba tiến trình, crash/reconciliation, ledger, chống trộn simulation/model và khôi phục archive. Model calls = 0. Xem [readiness giai đoạn 4](../reports/stage4-readiness.md), [kiểm định runner](../reports/pilot-runner-offline-validation.md), [schema](../docs/pilot-state-schema.md) và [hướng dẫn vận hành](../docs/pilot-runner.md).

R1 mới đạt hợp đồng/capture bằng fixture; chưa chọn runtime vận hành model hoặc kiểm định isolation/cleanup cho một model run thật. R2 có validator/importer nhưng review người thật vẫn 0/6. R3 có helper đối chiếu, chưa có adapter agent thật. R5 đã đạt trong scope simulation, chưa có provider pricing/usage thật. Các mục chưa được kiểm định thực tế tiếp tục để mở bên dưới.

## 1. Điểm xuất phát và hướng đi

Đã có sáu task B, 18 oracle/6 nop từ giai đoạn 2, bốn smoke B005/B006 và 41 test từ giai đoạn 3. Payload task và bằng chứng lịch sử không đổi. Dry-run đã có72 planned trial ID nhưng thiếu27 trường đầu vào và sáu task review pending; chưa gọi model.

Default WSL socket còn gián đoạn. Scoped Unix relay đã kiểm định cho lệnh development, tài khoản thường thực thi benchmark, socket0600 và dọn sau lệnh; chưa phải profile model đã được chọn. Nguyên nhân gốc của gián đoạn và outlier cũ chưa được xác định đầy đủ.

Giai đoạn này không lặp lại chẩn đoán cũ hoặc tăng số task để né các đầu vào thiếu. Ưu tiên readiness rõ trạng thái, quản lý run/cost/retry/resume và gói cấu hình cụ thể để người phụ trách có thể quyết định.

Có thể tiếp tục phần offline mà không cần baseline A hoặc API key. Phần thực thi model phụ thuộc đầu vào thật; mô phỏng không được gọi là kết quả benchmark model.

## 2. Mốc và điều kiện nghiệm thu

| Mốc | Sản phẩm | Điều kiện đạt |
|---|---|---|
| G4.1 — Readiness tự động | Gate đọc runtime/review/profile/budget theo snapshot | Trả rõ pass/fail/deferred; thiếu điều kiện thì không dispatch model |
| G4.2 — Runner offline | Scheduling, ledger, retry/resume và báo cáo thử | Dùng fake provider/fixture, không đọc secret hoặc gọi API; không trộn dữ liệu giả vào điểm model |
| G4.3 — Profile cụ thể | Hai cấu hình và runtime/network được chọn, mapping được kiểm định | Có đầu vào thật và đối chiếu effective config; không dùng placeholder làm cấu hình chạy |
| G4.4 — Smoke model | 1–2 trial theo ngân sách smoke riêng | Gate đạt, profile đúng và có ngân sách tương ứng trong phạm vi đã chốt |
| G4.5 — Native pilot | 72 trial B, coverage/cost/artifact đầy đủ | Kết quả thực hoặc báo phần thiếu, không lấy best-of-three |

Nếu chưa có reviewer/model/ngân sách, điểm kết thúc hợp lệ của đợt triển khai là G4.1–G4.2 cùng báo cáo deferred cụ thể. Không đánh dấu hoàn tất toàn bộ kế hoạch hoặc pilot từ kiểm định offline.

## 3. R0 — Đóng băng đầu vào và chuẩn hóa trạng thái

- [x] Kiểm tra checksum archive, manifest, task payload và prompt theo bằng chứng hiện có; không ghi đè report cũ.
- [x] Lập danh mục hiện trạng: đã có bằng chứng, thiếu đầu vào, chưa kiểm định, không áp dụng hoặc bị chặn kỹ thuật.
- [x] Tách snapshot task khỏi trạng thái máy: probe Docker mới không làm thay task version; thay hợp đồng chấm thì phải version hóa.
- [x] Dùng schema trạng thái chung thay cho suy đoán từ văn bản Markdown.
- [x] Mỗi trạng thái có nguồn bằng chứng, thời điểm, scope, snapshot hash và lý do; không có bằng chứng thì không pass.

**Trạng thái đề xuất:** `pass`, `fail`, `missing_input`, `unverified`, `not_applicable`. Trạng thái không đạt phải có hành động tiếp theo, không gộp mọi thứ thành một cờ boolean không giải thích được.

**Bàn giao:** `reports/stage4-input-state.json`, tài liệu schema và tham chiếu đến bằng chứng giai đoạn trước.

## 4. R1 — Runtime profile rõ ràng và attestation theo run

Hai lựa chọn hiện có cần được mô tả riêng:

| Profile | Điều kiện | Giới hạn |
|---|---|---|
| Native WSL default | CLI/engine thật của Harbor qua preflight hiện tại | Lịch sử có lỗi gián đoạn; không coi probe cũ là đủ |
| Scoped Desktop relay | Người vận hành chọn profile, đủ quyền WSL và lifecycle command-only | Workaround đã kiểm định development; không tự bật root hoặc mặc định dùng cho model |

**Đầu việc**

- [x] Tạo runtime profile có ID/version, distro/user, cơ chế kết nối, giới hạn thời gian và policy verifier offline.
- [x] Endpoint relay tạm được ghi làm bằng chứng mỗi run, không đưa đường dẫn ngẫu nhiên vào fingerprint ổn định làm các repeat thành cấu hình khác nhau.
- [x] Fingerprint chứa loại profile/version và policy; attestation kiểm endpoint thực tế, CLI/engine, user, socket mode/lifecycle và filesystem phù hợp profile đó.
- [x] Attestation gắn run ID và thời điểm, chỉ tái sử dụng trong phạm vi đã quy định; không dùng report khỏe của phiên trước để vượt một preflight đang fail.
- [x] Nếu default fail, báo fail; chỉ dùng scoped relay khi profile đó đã được chọn. Không chuyển âm thầm sang root/endpoint khác.
- [ ] Giữ Docker control socket ngoài agent/verifier; relay control plane không được hiểu thành quyền network API model.
- [ ] Cleanup chỉ tài nguyên do run này tạo; không restart dịch vụ chung, sửa socket toàn hệ thống hoặc prune cache của workload khác.
- [ ] Bổ sung test endpoint/profile mismatch, attestation sai run/snapshot, expired evidence và cleanup lỗi.

Không bắt buộc tìm ra mọi nguyên nhân của default socket để thực hiện thí nghiệm chẩn đoán bằng một profile khác đã được chọn và kiểm định. Tuy nhiên không được gọi workaround đó là sửa triệt để default integration.

**Nghiệm thu:** readiness phân biệt đúng hai profile; executor dùng đúng profile đã kiểm tra hoặc từ chối chạy. Không tái chạy toàn bộ24 trial khi chỉ cần một probe mới. Nếu chọn concurrency1, không bắt kiểm concurrency2; nếu chọn concurrency2, kiểm một smoke hạ tầng nhỏ tương ứng trước.

## 5. R2 — Bàn giao review và chấp nhận theo snapshot

- [x] Lập inventory hai gói review public/reference đã có, checksum và hướng dẫn thứ tự mở; không gửi ra ngoài nếu chưa được chỉ dẫn.
- [ ] Chủ dự án chỉ định reviewer khác tác giả; ghi người phụ trách và việc cần giao, không tự điền người review.
- [x] Chuẩn hóa review record: reviewer, ngày, task/prompt hash, thời gian giải thực đo, nhận xét và `accepted` hoặc `changes_requested`.
- [ ] Import kết quả review vào manifest có kiểm tra hash. Accepted của snapshot cũ không áp cho task đã thay đổi.
- [ ] Kiểm ràng buộc EN/VI và expected/verifier; giữ độ khó provisional nếu chưa đủ bằng chứng.
- [ ] Nếu có lỗi task thật: tăng version, sửa cả hai instruction khi cần và kiểm định lại đúng phạm vi bị ảnh hưởng.
- [x] Có báo cáo coverage review: 0..6 task đã accepted, thiếu reviewer hoặc còn thay đổi yêu cầu.

**Nghiệm thu:** không task nào tự được coi reviewed từ oracle/control pass; mọi task trong native pilot chính thức có chấp nhận đúng snapshot. Thiếu người review chỉ deferred phần này, không cản R3–R5 offline.

## 6. R3 — Hoàn thiện cấu hình cụ thể và fingerprint

Giữ template hiện tại để chỉ ra trường thiếu. Không tự chọn tên model, giá tiền hoặc credentials thay người phụ trách.

**Đầu vào cần chốt**

| Nhóm | Nội dung |
|---|---|
| Agent/model | Hai agent/version, model ID cụ thể, provider, endpoint, effort hoặc không áp dụng |
| Prompt/tools | Nội dung system prompt theo file/hash, tool access, kwargs được phép, kiến trúc host/container |
| Budget | Token/turn/time, trần smoke, inference/compute và concurrency |
| Runtime/network | Profile R1, cách gọi API, egress policy thực thi, verifier offline |
| Secret | Tên biến hoặc cơ chế cấp credentials, không lưu giá trị vào repo/report |

**Đầu việc có thể làm trước khi có model**

- [x] Bổ sung schema/validation cho profile, stable fingerprint và bảng trường cần đối chiếu.
- [x] Tách giá trị hành vi mô hình khỏi dữ liệu runtime tạm thời như socket path, timestamp hoặc job directory.
- [x] Fingerprint bao gồm agent/model/version, endpoint, effort, prompt content hash, kwargs/tool access, budget/resource/network policy có tác động.
- [x] Thiết kế bảng mapping profile → effective Harbor/agent config; fixture giả ghi rõ là mô phỏng.
- [ ] Chỉ mở kwargs theo allowlist của adapter được chọn, không nới thành dictionary tùy ý hoặc cho secret lọt vào log.
- [x] Có test thay đổi từng trường trọng yếu phải bị phát hiện, kể cả đổi nội dung prompt tại cùng đường dẫn.

**Khi đã có cấu hình thực**

- [ ] Đối chiếu mapping bằng config hiệu lực/khởi tạo agent đã khóa version; tham khảo source/tài liệu chính thức của đúng adapter khi triển khai.
- [ ] Kiểm tra API architecture phù hợp container offline hoặc egress được thực thi thật; không suy allowlist từ field cấu hình.
- [ ] Thêm trường hợp lỗi và usage/cost của provider đã chọn. Unknown error giữ trạng thái cần phân loại, không mặc định model fail.
- [ ] Lưu profile hoàn chỉnh và report diff giữa expected/effective config trước khi gọi model.

**Nghiệm thu:** helper dữ liệu thuần, adapter mô phỏng và adapter đã kiểm với agent thật có trạng thái khác nhau. Chỉ trạng thái cuối mới dùng cho pilot. Khi chưa có cấu hình, giữ thiếu đầu vào và không dựng fake model result.

## 7. R4 — Readiness gate có thể kiểm tra bằng máy

**Gate trước model dispatch**

- [ ] Snapshot task/prompt/verifier/config khớp manifest và không đổi sau khi review.
- [ ] Đủ task review accepted theo scope chạy.
- [ ] Runtime attestation đúng run/profile, preflight hiện tại đạt, filesystem và cách ly phù hợp.
- [ ] Profile model đầy đủ, effective mapping đã kiểm định, policy API/credentials rõ.
- [ ] Ngân sách còn đủ, cost estimate/reservation có cơ sở và smoke/pilot thuộc phạm vi đã chốt.
- [ ] Run manifest có expected configurations, planned trial ID, repeat và retry routing trước thực thi.
- [ ] Kind của run đúng: model, oracle/nop, dry-run và simulation không được trộn lẫn.

Gate trả danh sách lý do và bằng chứng cho từng điều kiện, không chỉ `ready=true`. Khi chưa đủ đầu vào, báo `missing_input`/`unverified` rõ ràng; không gọi API để “thử xem chạy được không”.

**Đầu việc**

- [x] Tạo `scripts/pilot_readiness.py` và output JSON có schema/version.
- [x] Giữ guard validation-only của runner oracle/nop; model runner là đường thực thi riêng.
- [x] Test từng gate fail độc lập, snapshot thay sau accepted, thiếu cả configuration và việc không dispatch khi bất kỳ gate bắt buộc nào chưa đạt.
- [x] Preview là tài liệu cho quyết định, không phải token tự bật thực thi; không suy quyền từ thời gian chờ hoặc một file cờ không rõ nguồn.

**Nghiệm thu:** có thể chứng minh bằng fake dispatcher rằng gate fail tạo0 model calls. Không hỏi lại quyết định đã được chốt trong session; chỉ cần bổ sung những trường thật sự còn thiếu.

## 8. R5 — Scheduling, cost ledger và retry/resume offline

Đây là phần triển khai có thể làm ngay mà chưa cần API key. Dùng fake provider hoặc recorded fixtures; kết quả thuộc namespace mô phỏng, không xuất hiện trong bảng điểm model.

**Scheduling và lưu trạng thái**

- [x] Planned trial ID ổn định cho mỗi config/task/language/repeat; attempt ID riêng, không đoán repeat từ tên folder.
- [x] Run manifest lập trước, seed/thứ tự rõ, đủ72 trial trong scope native-six.
- [x] Tách trạng thái `planned`, `reserved`, `submitted`, `completed`, `retryable_infra_error`, `verifier_error`, `agent_failure`, `uncertain` và `cancelled` với mapping công bố.
- [x] Ghi trạng thái bền vững trước/sau dispatch, cập nhật có tính idempotent; resume không tự gửi lại trial đã completed hoặc request chưa rõ đã được provider nhận.
- [x] Khi trạng thái submitted/chi phí chưa rõ sau gián đoạn, giữ uncertain và reconcile; không tự coi là chưa gọi API.

**Cost ledger**

- [ ] Ledger theo run/trial/attempt, tách smoke, inference và compute; giữ currency/unit và nguồn ước lượng.
- [x] Reserve một mức trần hợp lý trước dispatch, settle theo usage thực tế; request lỗi vẫn có thể phát sinh phí.
- [x] Thiếu bảng giá/usage/chi phí thì giữ unknown hoặc uncertain, không ép thành0 và không tự trả lại reservation.
- [ ] Chọn nguồn giá và cách tính khi có provider/model cụ thể; xác minh tại thời điểm triển khai, không điền giá giả vào profile thật.
- [x] Kiểm tổng trần trước mỗi dispatch và khi tăng concurrency; vượt/không đủ ngân sách thì dừng phần chưa chạy, báo coverage thiếu.

**Retry và resume**

- [x] Giữ tối đa hai retry bổ sung theo giao thức đã chốt; chỉ retry lỗi hạ tầng đủ bằng chứng, không retry lời giải sai để lấy pass.
- [x] Unknown provider error hoặc request có trạng thái nhận/charge chưa rõ không được retry mù.
- [x] Mỗi retry giữ planned identity, tăng attempt và giữ toàn bộ raw reference/chi phí.
- [ ] Resume xác minh snapshot/runtime/profile trước khi chạy tiếp; thay cấu hình phải tạo run mới hoặc phân tích riêng.
- [x] Có kiểm định crash sau reserve, sau submit, trước persist result; test double-start, thiếu cả config, null reward, rate limit và chạm trần chi phí.

**Nghiệm thu:** một run mô phỏng72 trial có thể dừng/resume mà không nhân đôi dispatch hoặc làm mất cost/attempt; raw→normalized→coverage/score đối chiếu được. Rate limit/retry fixture không thay thế kiểm định provider thật. Không coi resume trong harness là bảo đảm provider hỗ trợ idempotency.

**Bàn giao:** state schema, `scripts/pilot_runner.py` với chế độ simulation mặc định, ledger và `reports/pilot-runner-offline-validation.md`. Chế độ model không tự bật khi thiếu R2–R4.

## 9. R6 — Kiểm định sẵn sàng và bàn giao cấu hình để quyết định

- [x] Lập report readiness mới, giữ nguyên report giai đoạn3.
- [x] Liệt kê rõ điều gì đã kiểm định offline, điều gì đã kiểm với runtime/agent thực tế và đầu vào nào còn thiếu.
- [ ] Nếu đã có model/ngân sách, tạo preview concrete: scope, cấu hình, số trial, estimate/reservation, lệnh dự kiến và điều kiện dừng.
- [x] Nếu chưa có, bàn giao template và danh sách thiếu; không chỉ báo chung chung “cần xác nhận”.
- [ ] Đối chiếu review bundle/accepted snapshot, canonical hashes, endpoint class và cleanup policy.
- [x] Chỉ chạy lại control có liên quan khi thay code/runtime/task hoặc còn lỗi chưa giải quyết. Không lặp toàn bộ test/task để tạo thêm số liệu đẹp.

**Nghiệm thu:** người phụ trách có thể đánh giá một cấu hình cụ thể hoặc biết chính xác còn thiếu gì. Không phát sinh gửi email/tin nhắn, upload dữ liệu hoặc phát hành từ bước này.

## 10. R7 — Smoke model và native pilot, có điều kiện

Chỉ bắt đầu khi R2–R4 đạt, runtime/profile được chọn và ngân sách đã có trong phạm vi cho phép. Không dùng kết quả mô phỏng để vượt gate này.

- [ ] Smoke1–2 trial model theo budget riêng; kiểm auth, tools, artifact, reward, usage và ledger thực tế.
- [ ] Lỗi profile/hạ tầng được điều tra trước pilot; giữ attempt/cost, không giả là model fail.
- [ ] Đóng băng run chính:6 task B ×2 instruction ×3 repeat ×2 cấu hình = **72 trial**, chưa gồm smoke/retry.
- [ ] Trộn thứ tự, không chia sẻ lịch sử, môi trường sạch và ngân sách tương đương EN–VI.
- [ ] Theo dõi cost, uncertain requests, coverage và lỗi; dừng an toàn khi budget/runtime không còn đạt.
- [ ] Xuất raw/normalized/ledger, macro score theo nhóm, delta EN–VI và CI hoặc lý do không ước lượng được.
- [ ] Không gọi “ít nhất một pass trong ba lần” là pass@1; không trộn control/simulation vào model score.
- [ ] Review lỗi và hạn chế; task thay đổi phải version hóa và đánh giá lại đối xứng.

**Bàn giao:** `reports/native-model-pilot.md`, cấu hình và archive Linux. Nếu chưa chạy, không tạo report chứa kết quả model giả hoặc đánh dấu mốc này hoàn tất.

## 11. R8 — Phần A, test kín và phát hành

- [ ] Phần A chờ snapshot/config/quyền dùng từ Eval theo [checklist](../docs/eval-input-checklist.md); không tự dựng bài rồi gọi là bản dịch Terminal-Bench.
- [ ] Nếu đủ đầu vào A, chọn sáu task, dịch/review bốn biến thể và thêm144 trial để thành216; giữ A/B là hai phép đo riêng.
- [ ] Tập kín theo [thiết kế family](../docs/private-test-design.md); sáu task đã lộ vẫn là development.
- [ ] Không ép tạo đủ private set trước pilot chẩn đoán; CI B hiện null khi một family/skill vẫn là kết quả trung thực.
- [ ] License, hosting và phát hành là quyết định riêng của chủ dự án; không upload hoặc publish mặc định.

Các mục này có điều kiện, không ngăn hoàn thiện runner offline hoặc native pilot đã đủ đầu vào.

## 12. Thứ tự và thời gian đề xuất

```text
R0 → R1 runtime contract ─────────┐
R2 review khi có người ───────────┤
R3 schema/template → mapping thật ┤→ R4 gate → R6 concrete readiness → R7 model pilot
R5 offline runner/ledger ─────────┘
R8 A/private/release: nhánh có điều kiện, không chặn phần B/offline.
```

| Công việc | Ngày làm việc ước lượng | Đầu vào bên ngoài |
|---|---:|---|
| R0/R1 state và runtime contract | 1–2 | Profile vận hành cần được chọn trước model run |
| R3/R4 schema, mapping contract, readiness gate | 1–2 | Agent thật mới kiểm định mapping thực tế được |
| R5 scheduling/ledger/retry/resume offline | 2–3 | Không cần API key hoặc baseline A |
| R6 report và gói bàn giao | 1 | Tổng hợp điều kiện còn thiếu |
| Review thực, smoke và pilot model | Ước lượng sau | Reviewer, model/budget, profile và runtime |

Khoảng5–8 ngày làm việc cho phần kỹ thuật offline là ước lượng lập kế hoạch, không cam kết tốc độ phát hiện lỗi hoặc thời gian chờ reviewer. Giữ phiên bản Harbor/Python/image đã khóa; không nâng dependency hoặc đổi task để né điều kiện thiếu.

## 13. Definition of Done

- [x] Snapshot/bằng chứng lịch sử được bảo toàn và trạng thái mới có scope/thời điểm.
- [ ] Runtime profile rõ ràng, không silent fallback; attestation và cleanup được kiểm định.
- [x] Review records được kiểm theo hash; pending không tự thành accepted.
- [x] Profile template/mapping contract có validation và fingerprint đầy đủ; phân biệt simulated/real-verified.
- [x] Readiness gate ngăn dispatch khi thiếu điều kiện, trả lý do cụ thể.
- [x] Offline runner72 trial qua retry/resume/cost/crash tests mà không gọi API hoặc trộn vào model score.
- [x] Có report bàn giao cụ thể và danh sách đầu vào còn thiếu.
- [ ] Chỉ khi chạy thực: có smoke/native model report, cost ledger và raw archive.
- [x] Phần A, private test và phát hành giữ deferred khi chưa có đầu vào/quyết định.
- [x] Cập nhật kế hoạch/readiness theo bằng chứng thật, không đánh dấu hoàn thành pilot từ dry-run.

**Việc bắt đầu khi triển khai:** R0, schema readiness R4 và state/ledger offline R5; kế thừa guard/runtime đã có. Chuẩn bị bàn giao R2/R3 trong lúc chờ đầu vào, không tự lặp thêm task hoặc paid run.
