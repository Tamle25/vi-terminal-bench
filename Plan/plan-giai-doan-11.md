# Kế hoạch giai đoạn 11 — Hoàn thiện bản benchmark B nhỏ dùng được

- Ngày lập: 13/11/2026, Asia/Saigon.
- Trạng thái cập nhật 13/11/2026: **hoàn thành bản nhỏ development dùng được**; 36/36 trial model hợp lệ, 35 pass; 223/223 test Linux đạt, report/resume/archive restore đã kiểm. Xem [kết quả](../reports/development-benchmark-results.md), [readiness](../reports/stage11-readiness.md) và [quickstart](../docs/development-benchmark-quickstart.md).
- Mục tiêu do người dùng chốt: **bản nhỏ dùng được**, với sáu task B, một cấu hình model/agent và kết quả đánh giá tái lập được.
- Kế thừa: [readiness giai đoạn 10](../reports/stage10-readiness.md), [summary](../reports/stage10-summary.json), [thiết kế agent](../docs/terminal-agent-design.md) và [giao thức đánh giá](../docs/evaluation-protocol.md).
- Đích nghiệm thu: **6 task × 2 instruction EN/VI × 3 repeat × 1 cấu hình = 36 trial hợp lệ**, có raw artifact, verifier reward, trajectory, usage/chi phí và báo cáo.
- Nhãn kết quả: **development / internal — chưa review độc lập**. Review độc lập không chặn chạy nội bộ; trạng thái review/attribution thật được giữ nguyên.

## 1. Điểm xuất phát

Đã có sáu task B, oracle, verifier, controls, instruction EN/VI; 203/203 kiểm thử Linux đạt. Host agent, controller, HTTP worker, artifact transfer và ledger đã kiểm offline. Có một request provider-connectivity thật ở giai đoạn 9; chưa có task benchmark nào được model thực hiện.

| Khoảng trống hiện tại | Việc phải giải quyết trong giai đoạn 11 |
|---|---|
| Docker/WSL chưa hoạt động ở lần probe cuối | Khôi phục runtime và kiểm lifecycle container thực |
| Gate thật vẫn yêu cầu human acceptance | Thêm giao thức/scope development cho phép task pending, có provenance rõ |
| Controller/config/verifier mới gắn B001 | Tổng quát hóa cho sáu task, repeat và manifest 36 trial |
| Dự phòng input toàn model giữ tiền lớn | Kiểm bound/settlement để ngân sách nhỏ có thể chạy nhiều request mà vẫn có cap |
| Compute local đang đòi quote như hạ tầng tính phí | Phân biệt thời gian máy local không đo phí với dịch vụ compute tính phí |
| Schema smoke chưa đi thẳng vào aggregate | Nối raw → normalized → coverage → report bằng scope development riêng |

Các việc này thuộc cùng kế hoạch. Khi phát sinh lỗi runtime/adapter/verifier, sửa và kiểm lại tại đây; tiến độ được tính theo bằng chứng chạy thực và 36 trial, không theo số plan hoặc số unit test bổ sung.

## 2. Mốc nghiệm thu

| Mốc | Sản phẩm | Điều kiện đạt |
|---|---|---|
| G11.1 — Runtime và development gate | Runtime hoạt động, policy thử nội bộ có version | Container fixture chạy thật; pending review không chặn scope development; các gate khác vẫn được thực thi |
| G11.2 — Backend đủ sáu task | Controller, image/artifact/verifier mapping và normalization | Oracle/no-op đi qua backend mới đúng kỳ vọng cho cả sáu task |
| G11.3 — Smoke model thật | B001 EN/VI, một cấu hình, hai trial riêng | Có terminal trajectory, artifact, verifier và accounting thực; phân biệt reward với tính hợp lệ của đường chạy |
| G11.4 — Bản nhỏ dùng được | Run 36 trial, báo cáo và CLI tái lập | Đủ 36 trial hợp lệ; lỗi agent là kết quả, lỗi hạ tầng chưa giải quyết không được tính thành reward 0 |

Hai trial smoke là kiểm tra riêng, không lấy kết quả smoke điền vào 36 trial chính. Reward thấp không làm mất tính hợp lệ của một benchmark chạy đúng; không có ngưỡng điểm model bắt buộc để nghiệm thu công cụ.

## 3. W0 — Đóng băng phạm vi và kiểm lịch sử

- [x] Đối chiếu snapshot task/prompt, source, report và archive giai đoạn 10; tài liệu trạng thái cũ kiểm theo bản archive, không sửa report cũ để khớp code mới.
- [x] Kiểm receipt/ledger connectivity read-only, giữ exposure 0,01 USD và invoice còn thiếu. Không gửi lại connectivity hoặc đọc key để lập inventory.
- [x] Chọn một cấu hình ban đầu từ model đã kết nối, ghi model snapshot, agent/version, system prompt, tool schema và giới hạn; xác minh compatibility/giá khi chuẩn bị thực thi.
- [x] Giữ đủ sáu task hiện có: B001 hóa đơn, B002 Unicode/tên file, B003 Windows-1258, B004 tìm không dấu, B005 collation và B006 CSV.
- [x] Ghi input state, điểm cần sửa của backend và các đầu vào vận hành còn thiếu. Tái sử dụng quyền/quyết định đã có, không hỏi lại model/key/trần kiểm thử đã chốt.

**Bàn giao dự kiến:** `reports/stage11-input-state.json` và `reports/stage11-run-spec.md`.

## 4. W1 — Giao thức thử nội bộ không chờ reviewer

Đây là thay đổi phạm vi theo mục tiêu mới của người dùng. Yêu cầu review của pilot/phát hành trước đây vẫn giữ ý nghĩa; bản development có đường thực thi riêng.

- [x] Version hóa protocol/schema với scope `development-smoke` và `development-batch`; cho phép một cấu hình và task `review_status=pending`.
- [x] Tách gate review khỏi gate runtime, source/config, credential, isolation, budget và dispatch. Chỉ scope development được miễn điều kiện acceptance; không sửa template thành accepted hoặc dùng fixture signoff.
- [x] Đưa `review_status`, `development_only`, source snapshot và attribution vào manifest, normalized record và report. Giữ tác giả `Codex-assisted` theo dữ liệu thực.
- [x] Khai báo rõ trial smoke và batch; aggregator không trộn hai scope hoặc đưa record development thành reviewed pilot/release.
- [x] Lập cơ chế xác nhận effective config từ controller/backend thật. Presence của key, preview pass hoặc JSON `ready=true` không tự mở dispatch.
- [x] Kiểm scope mới không mở gate cũ của pilot 72 trial hoặc cho phép model truy cập oracle/test kín.

**Bàn giao:** protocol development có version, contract/gate mới và kiểm regression cho scope thật/fixture/reviewed/development.

## 5. W2 — Khôi phục runtime và kiểm container thực

- [x] Chẩn đoán lại Docker Desktop/WSL integration, CLI/engine/socket/user/endpoint; ghi đúng lỗi hiện tại thay vì mặc định probe cũ vẫn đúng.
- [x] Sửa cấu hình thuộc dự án và runtime trong quyền vận hành đã có. Nếu cần thao tác giao diện Docker Desktop, nêu đúng bước cần người vận hành thực hiện; không tự restart/prune workload chung hoặc âm thầm đổi endpoint.
- [x] Chọn runtime Linux hoạt động, concurrency 1, job/artifact/ledger trên storage Linux bền vững. Kiểm case-distinct và NFC/NFD trước copy/transfer.
- [x] Kiểm build source/image identity, create/start/exec, timeout process group, pause/transfer, separate verifier và cleanup. Dùng fixture không gọi model trước.
- [x] Bảo đảm host API client giữ key; agent/verifier không có `.env`, key, oracle, expected hoặc Docker control socket. Thực thi mạng/resource policy bằng backend thật.
- [x] Kiểm deadline worker, container TTL, timeout verifier và cleanup khi lỗi. Capture attestation mới đúng run/snapshot/profile, kiểm lại khi hết hạn.

**Điều kiện qua W2:** có evidence container thực. Nếu Docker chưa được khôi phục, tiếp tục W1/W3/W4/W5 phần độc lập; giữ mốc runtime chưa đạt và hướng dẫn sửa cụ thể trong cùng giai đoạn.

## 6. W3 — Tổng quát backend cho sáu task

Không chỉ đổi task ID trong config B001. Cần kiểm đường chạy và grader tương ứng của từng task.

- [x] Đưa task selection vào registry whitelist từ manifest; loại hardcode B001 trong config validation, review/development gate, image build và controller.
- [x] Đọc resource/time/artifact contract của đúng `task.toml`, đóng băng effective policy và áp dụng giống nhau cho EN/VI/repeat của task đó.
- [x] Build image agent/verifier riêng theo đúng context, base digest, task version và payload hash. Không copy thư mục repo hoặc test/solution vào agent image.
- [x] Tổng quát hóa artifact mapping: B002 có `/app/incoming`, các task khác dùng contract riêng; kiểm nguồn không đổi, file nhị phân, tên NFC/NFD và case-distinct sau transfer.
- [x] Kiểm runtime đặc thù B005, gồm Node/ICU/CLDR theo task đã khóa; không thay bằng collation host hoặc thư viện khác rồi coi cùng cấu hình.
- [x] Chạy verifier riêng của từng task; mapping exit/reward/status nhất quán. Nguồn dữ liệu là artifact, không thực thi code agent tạo trong verifier.
- [x] Thêm identity `task_id`, `family_id`, `language`, `repeat`, `configuration`, `attempt` vào state/trajectory/receipt/output; không để sáu task đè chung ID hoặc output directory.
- [x] Kiểm oracle pass và no-op fail qua backend mới cho từng task. Dùng container sạch và reference chỉ cho kiểm định; model run không kế thừa file/lịch sử/reference.
- [x] Nếu đổi môi trường hoặc hợp đồng ảnh hưởng độ khó/verifier, version hóa và kiểm lại phần liên quan ở cả EN/VI; giữ source và kết quả cũ.

**Bàn giao:** registry sáu task, policy/image/artifact/verifier mapping và `reports/stage11-container-validation.md`.

## 7. W4 — Ngân sách thực dụng, có cap và recovery

Trần kiểm thử 2 USD đã có trong hội thoại. Khi thực hiện, áp dụng quyền đó đúng scope được phép, tính cả exposure/request đã phát sinh; không hỏi lại cùng quyết định hoặc tự tăng trần. Chưa có căn cứ khẳng định 2 USD đủ cho toàn bộ 36 trial.

### Giải quyết reservation trước khi mở batch

Giai đoạn 10 giữ 0,208608 USD/request theo full-model input bound. Với bốn request/trial, riêng 36 trial có reservation tối đa **30,039552 USD** theo đơn giá lịch sử trong run spec; đó là dự phòng, không phải chi phí thực. Giữ nguyên chính sách này sẽ không phù hợp mục tiêu chạy nhiều trial với ngân sách nhỏ.

- [x] Đo usage/context thật từ smoke và xác minh nguồn giá hiện hành trước khi tính budget batch; tính cả system/tool schema, history và tool output.
- [x] Chọn bound nhỏ hơn chỉ khi có cơ sở kiểm được về tokenizer/request serialization hoặc cơ chế count tương thích. Không dùng một hệ số ký tự/token tùy ý làm bảo đảm chi phí.
- [x] Xác định policy settlement có version: khi usage/model/tier/fee mapping đầy đủ có thể ghi charge dự kiến bảo thủ theo receipt và hoàn phần reservation thừa theo policy đã công bố; giữ estimate khác invoice và giữ quỹ dự phòng correction. Không sửa policy ledger cũ tại chỗ hoặc gọi estimate là hóa đơn.
- [x] Timeout, thiếu receipt/usage, model/tier/fee chưa biết vẫn giữ reservation/uncertainty và chặn phần cần chặn. Không release vì request lỗi hoặc lookup không thấy.
- [x] Nếu chưa kiểm được bound/settlement mới, tiếp tục dùng policy thận trọng và ghi ngân sách cần thiết; không hạ reservation chỉ để làm config pass.

### Compute, pool và tiếp tục run

- [x] Với Docker trên máy local không có charge provider riêng: ghi thời gian/CPU/RAM và `compute_cost_status=not_metered`; không ép có báo giá cloud hoặc tự quy đổi thành USD. Đây là chi phí chưa đo, không phải tuyên bố tổng compute cost bằng 0.
- [x] Nếu dùng dịch vụ compute tính phí, bổ sung quote/cap và compute reserve tương ứng. Phân biệt preparation/build với trial execution.
- [x] Dùng persistent shared ledger, import exposure cũ idempotent và giữ mọi request/attempt. Có cap pool/run/trial và kiểm/reserve trước mỗi request; không vượt trần bằng mở DB hoặc output folder mới.
- [x] Cho phép tiếp tục **trial chưa gửi** khi manifest/source/config không đổi, runtime mới đạt và ledger cho phép. Trial đã hoàn tất không chạy lại; partial request/tool thiếu checkpoint không tự replay.
- [x] Đóng băng retry policy trước batch; mặc định không retry tự động. Nếu cần sửa lỗi hạ tầng và thử lại, giữ attempt cũ, bằng chứng chi phí và routing mới theo hợp đồng, không lấy lần reward cao nhất.
- [x] Khi dự toán batch vượt quyền ngân sách hiện có, hoàn thiện run spec, số request/bound, chi phí smoke và khoản cần thêm trước khi yêu cầu quyết định mới. Dừng trước khi vượt cap; không báo MVP hoàn thành khi mới chạy một phần.

**Bàn giao:** budget/settlement policy, effective config, ledger/recovery contract và dự toán smoke/batch có cơ sở.

## 8. W5 — Một CLI chạy và xuất báo cáo

- [x] Cung cấp entrypoint thống nhất cho `validate`, `plan`, `run`, `resume-unstarted` và `report`, tên lệnh chốt khi triển khai; preview/plan không đọc key hoặc gửi API.
- [x] Lập manifest **36 planned trial ID trước khi chạy**, gồm sáu task, EN/VI, repeat 1–3, một cấu hình; seed/thứ tự được lưu và cân bằng ngôn ngữ. Không tạo trial ID hậu kiểm từ tên thư mục.
- [x] Freeze source, dataset/prompt, image/policy, model/agent/tools/limits, budget và origin development. Smoke là run riêng, không nhập vào batch coverage.
- [x] Chuyển controller output thành JSONL tương thích aggregator bằng adapter có version; giữ raw reference, request IDs, attempt routing và billing overlay. Không đổi nhãn scope để vượt guard aggregate cũ.
- [x] Báo coverage theo task/ngôn ngữ/repeat, số valid/infra/missing/uncertain; lỗi agent có reward 0, lỗi hạ tầng/verifier chưa giải quyết có reward null.
- [x] Xuất JSON/CSV và Markdown: điểm từng task, EN/VI, nhóm năng lực, delta EN–VI, thời gian, token, chi phí đã biết/chưa biết và lỗi.
- [x] Giữ phương pháp macro/repeat của giao thức; không dùng best-of-three. Với một family/nhóm, CI không đủ cơ sở phải để null kèm lý do; chưa dùng kết quả nhỏ để xếp hạng tổng quát.
- [x] Viết hướng dẫn từ workspace sạch: chuẩn bị runtime/key, preview, run, tiếp tục phần chưa gửi, report và đọc lỗi; lệnh thực tế được kiểm trước bàn giao.

**Bàn giao:** CLI, adapter/schema, run plan/config mẫu và `docs/development-benchmark-quickstart.md`.

## 9. W6 — Smoke model thật rồi chạy 36 trial

### Smoke riêng: hai trial B001

- [x] Sau gate/runtime/budget đạt, chạy một trial EN và một VI của B001, cùng cấu hình/limits, container và history độc lập.
- [x] Thu tool trajectory thật, artifact/verifier, provider ID/usage/cost, deadline và cleanup; không gửi thêm connectivity để thay thế.
- [x] Đánh giá tính hợp lệ đường chạy riêng với reward. Nếu model không sử dụng terminal, chưa có bằng chứng đường terminal hoạt động; điều tra trước khi mở batch. Giải sai không phải lý do retry để tăng reward.
- [x] Đối chiếu chi phí và ledger, sửa lỗi backend nếu có rồi kiểm lại đúng phần bị ảnh hưởng. Chốt cấu hình/giới hạn cho batch trước khi nhìn kết quả batch.

### Batch chính: 36 trial

- [x] Gate và manifest cuối đạt; chạy concurrency 1 theo thứ tự đã freeze, giữ cùng điều kiện EN/VI trong mỗi task và history độc lập cho mọi repeat.
- [x] Kiểm budget/attestation/state trước từng request và trial; refresh evidence hợp lệ khi cần mà không đổi stable configuration.
- [x] Khi gặp lỗi hạ tầng, lưu state/receipt và sửa nguyên nhân trong giai đoạn này. Không bỏ task khó, thay prompt sau kết quả hoặc biến infra failure thành agent fail.
- [x] Nếu thay task/verifier/config làm điều kiện không còn khớp, lập version/run tương ứng và đánh giá lại phần cần thiết; không gộp kết quả khác snapshot thành đủ 36.
- [x] Tiếp tục đúng phần chưa gửi theo ledger; unknown/partial cần reconcile trước. Không chạy lại trial đã hoàn tất để cải thiện reward.
- [x] Kết thúc khi có **36 trial hợp lệ**, đủ 6 × 2 × 3. Nếu cap hoặc điều kiện ngoài dự án khiến chưa đạt, báo rõ số đã chạy/còn thiếu và giữ trạng thái chưa nghiệm thu.

**Bàn giao:** `reports/development-benchmark-smoke.md`, raw/normalized/provenance/ledger theo run ID và `reports/development-benchmark-results.md`.

## 10. W7 — Kiểm tái lập và đóng gói bản nhỏ

- [x] Kiểm đủ planned ID, mapping raw → normalized → aggregate, status/reward và phí của mọi attempt; không cộng trùng smoke, retry hoặc invoice revision.
- [x] Tái tạo báo cáo từ raw/normalized đã lưu bằng CLI, không cần gọi API lại. Chỉ chạy thêm model khi có lý do kiểm riêng và budget tương ứng.
- [x] Archive trên filesystem Linux; kiểm hash và restore ledger/artifact/trajectory, giữ NFC/NFD/case-distinct. Dùng allowlist, không archive `.env` hoặc Authorization.
- [x] Đóng gói config/schema/version, hướng dẫn, kết quả 36 trial, trạng thái task pending review và giới hạn development; nguồn/license giữ đúng thực tế, chưa gắn nhãn đã phát hành chính thức.
- [x] Cập nhật README/kế hoạch tổng thể/readiness theo evidence. Kiểm regression phù hợp với thay đổi, không lấy fixture pass hoặc tăng test count thay nghiệm thu thực.

**Bàn giao:** `reports/stage11-summary.json`, `reports/stage11-readiness.md`, gói evidence và quickstart đã kiểm.

## 11. Thứ tự thực hiện và xử lý vướng mắc

```text
W0 phạm vi/lịch sử → W1 development policy → W3 backend sáu task → W5 CLI/report
              └→ W2 runtime ──────────────────────────────────────────────┤
              └→ W4 budget/settlement/recovery ────────────────────────────┤
                                                   W6 smoke → 36 trial → W7 bàn giao
```

Các nhánh có thể tiến hành độc lập, không yêu cầu nhiều agent. Khi một nhánh chờ thao tác vận hành hoặc quyết định ngân sách, hoàn tất phần không phụ thuộc nhánh đó. Vướng mắc và việc sửa được theo dõi trong chính plan 11; không mặc định cần thêm một plan để đạt bản nhỏ.

| Tình huống | Cách xử lý |
|---|---|
| Chưa có reviewer | Vẫn chạy scope development khi các gate khác đạt; giữ review pending và nhãn internal |
| Docker/WSL fail | Chẩn đoán/sửa đúng quyền, nêu thao tác ngoài dự án nếu cần; làm tiếp code/CLI/kiểm offline độc lập |
| Local compute chưa đo phí | Ghi not-metered và thời gian tài nguyên; không tạo rào cản quote cloud giả |
| Cap hiện có chưa đủ batch | Đưa dự toán và tiến độ thật để chốt ngân sách; không tự tăng hoặc ghi 36 trial đã hoàn tất |
| Provider/tool uncertain | Giữ exposure/state, reconcile trước; không resend hoặc reset ledger |
| Agent reward 0 | Giữ kết quả hợp lệ, tiếp tục theo manifest khi gate còn đạt |

## 12. Definition of Done — bản nhỏ dùng được

- [x] Sáu task B có registry/image/artifact/verifier mapping được kiểm trên backend Linux thật.
- [x] Scope development cho phép pending review, giữ metadata/attribution thật và không mở scope reviewed/release.
- [x] Có CLI và quickstart thực tế để plan/run/tiếp tục trial chưa gửi/report cho một cấu hình.
- [x] Smoke B001 EN/VI chứng minh model–terminal–artifact–verifier/accounting hoạt động thực.
- [x] Có đủ **36 trial hợp lệ**; reward 0 được giữ, infra/missing/uncertain không bị che thành kết quả đầy đủ.
- [x] Báo cáo JSON/CSV/Markdown tái tạo được từ evidence, có điểm, coverage, lỗi, thời gian/token và cost status rõ.
- [x] Budget/gate/recovery được thực thi, không vượt quyền bằng retry ẩn hoặc đổi state folder.
- [x] Archive/restore đạt, không có credential và giữ đúng bytes/tên Unicode.
- [x] README/readiness ghi đúng trạng thái **bản nhỏ development dùng được, chưa review độc lập** và các giới hạn.

Chỉ đánh dấu giai đoạn hoàn tất khi đủ các điều kiện trên. Một plan đủ tổ chức toàn bộ công việc này; số ngày và tổng phí cần căn cứ runtime và smoke thực tế.

**Bước đầu khi được yêu cầu triển khai:** W0–W2, đồng thời kiểm các điểm hardcode B001 và policy reservation/local compute; ưu tiên sớm có container fixture thật rồi smoke model, sau đó hoàn tất batch 36 trial trong cùng giai đoạn.

## 13. Kết quả triển khai

G11.1–G11.4 đạt cho scope development/internal. Runtime mặc định Ubuntu từng hoạt động rồi timeout; đã chọn explicit shared container proxy qua relay v2, không sửa socket hệ thống/restart workload. Collector được sửa để đọc tmpfs qua trusted tar stream; verifier nhận artifact stdin thay bind path distro. Sáu oracle pass/sáu no-op fail, B005 runtime đúng bản khóa.

Giữ full-model input reservation, không giả có tokenizer bound nhỏ hơn. Policy settlement development chỉ hoàn reserve thừa khi receipt/usage/price mapping đủ, giữ margin và unknown; cap 2 USD dùng chung smoke/batch/exposure cũ. Compute local not-metered, không ép quote cloud hoặc gọi cost bằng 0. Review vẫn pending, attribution không đổi, gate pilot cũ không mở.

Smoke001 và smoke002 là bốn trial riêng, không nhập coverage batch; source và mọi phí giữ đủ. Batch có một gate-blocked intent trước HTTP, checkpoint/audit chứng minh chưa dispatch, không tool; đã re-arm slot chưa gửi và giữ 25 kết quả cũ, gồm một reward 0. Controller CPU 0 không tái hiện clock/attestation jitter trong probe và phần tiếp tục. Không retry lời giải sai hoặc sửa model/task/prompt/limits giữa batch.

Kết quả chính: **35/36 pass**, EN 17/18 (94,44%), VI 18/18 (100%), delta +5,56 điểm phần trăm; CI null do một family/nhóm. Batch có 76 response provider, token estimate bảo thủ 0,11385825 USD; cả stage11 có 85 response, cộng connectivity trước là 86 response, tổng estimate bảo thủ 0,1349925 USD. Một intent bị chặn không tính là response provider. Chưa có invoice; holds không cộng thành fee.

Hồi quy cuối **223/223 Linux test**, zero skip. Dựng lại report khớp byte JSONL/CSV/Markdown; completed resume tạo 0 request; toàn bộ artifact hash và ledger outcome khớp. Native archive restore đạt 604 file, giữ Unicode/case-distinct; source/runtime/recovery evidence có hash. Các checkbox điều kiện chỉ xét scope nội bộ; cloud quote/tokenizer bound nhỏ hơn không áp dụng trong cấu hình này. Review độc lập, giấy phép phát hành, phần A và pilot hai cấu hình vẫn là các mốc khác.
