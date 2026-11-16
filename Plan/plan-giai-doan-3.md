# Kế hoạch giai đoạn 3 — Ổn định môi trường và chuẩn bị pilot model

- Ngày lập: 12/11/2026.
- Kế hoạch tiếp nối: [plan-giai-doan-4.md](plan-giai-doan-4.md), chưa triển khai; tập trung readiness có thể kiểm tra bằng máy và pilot runner offline.
- Trạng thái cập nhật 12/11/2026: đã triển khai chẩn đoán, guard/process, workaround relay có phạm vi,4 smoke pass,41 test, gói review, model dry-run và thiết kế test kín. Default WSL vẫn gián đoạn; review độc lập/model profile thật/pilot còn chờ.
- Kế thừa: [giai đoạn 2](plan-giai-doan-2.md), [kiểm định native-six](../reports/native-six-validation.md), [pilot readiness](../reports/pilot-readiness.md).
- Ưu tiên: xử lý đường Docker CLI qua WSL và nhiễu verifier, giữ nguyên bằng chứng task đã kiểm định.
- Phạm vi triển khai không phụ thuộc model: chẩn đoán/sửa hạ tầng, kiểm định có mục tiêu, hồ sơ review, cấu hình và dry-run pilot.
- Pilot có phí và phần A chỉ thực hiện khi đủ đầu vào; không coi việc viết kế hoạch này là chọn model, ngân sách hoặc cấp quyền phát hành.

## 1. Điểm xuất phát

Theo báo cáo cuối giai đoạn 2:

| Thành phần | Bằng chứng hiện có | Giới hạn |
|---|---|---|
| Sáu task B | EN/VI, oracle, alternative, grader riêng | Chưa review độc lập, độ khó chưa hiệu chỉnh |
| Kiểm định Harbor | 18/18 oracle reward 1; 6/6 nop reward 0 | Đây là control, không phải model score |
| Kiểm định công cụ | 125 controls và 27 test đạt | Không chứng minh mọi điều kiện vận hành ổn định |
| Artifact | Linux filesystem, archive khôi phục được | Không đặt raw artifact nhạy tên file trên Windows |
| Hash | Canonical relative POSIX, khớp Windows/Linux và manifest | Snapshot M1 cũ giữ quy ước lịch sử, không ghi đè |
| Docker/WSL | Windows API phản hồi; WSL CLI cuối phiên timeout 30 giây | Preflight cuối `ready=false`; phải xác minh lại khi triển khai |
| Latency | Hai pha verifier repeat 1 khoảng 1.071/1.072 giây; các lượt sau bình thường | Chưa có nguyên nhân gốc, không dùng để suy tốc độ agent |
| Thực nghiệm | Manifest trước chạy, adapter, coverage, family bootstrap | Profile mới cho model/network chưa được kiểm định |

Không mặc định Docker hiện vẫn lỗi hoặc đã tự hồi phục. Bước đầu tiên là đo lại có giới hạn và ghi bằng chứng mới, tách khỏi các báo cáo lịch sử.

## 2. Mốc và điều kiện chuyển bước

| Mốc | Đầu ra | Điều kiện đạt |
|---|---|---|
| G3.1 — Chẩn đoán | Báo cáo CLI/endpoint/process/timing | Phân biệt được lỗi engine, CLI, WSL integration hoặc subprocess; có bằng chứng tái hiện hoặc ghi rõ chưa tái hiện |
| G3.2 — Hạ tầng đủ chạy thử | Preflight và smoke có mục tiêu | Không treo vô hạn; đường CLI thực tế của Harbor hoạt động; giữ đúng Unicode, reward và cách ly |
| G3.3 — Pilot chuẩn bị xong | Review records, model profile, kế hoạch run và dry-run | Biết rõ những đầu vào còn thiếu; không gọi API khi cấu hình/ngân sách chưa có |
| G3.4 — Native pilot | 72 trial model thuộc phần B và báo cáo | Review đạt; model/ngân sách/API rõ; hạ tầng qua kiểm tra; chạy đúng giao thức |
| G3.5 — Full pilot, có điều kiện | Thêm 144 trial phần A, tổng 216 | Có sáu task A và baseline/quyền dùng tương thích |

Đạt G3.2 không đồng nghĩa task đã được reviewer chấp nhận. Đạt G3.3 về công cụ không đồng nghĩa được chạy model nếu cấu hình/ngân sách còn thiếu. B-only được phép là một thí nghiệm riêng, không chờ vô thời hạn phần A.

## 3. Q0 — Bảo toàn bằng chứng và ghi trạng thái mới

- [x] Kiểm tra archive M1/native-six và các run manifest vẫn còn; đối chiếu checksum đã ghi.
- [x] Lưu report chẩn đoán với run ID/ngày mới, không ghi đè kết quả cuối giai đoạn 2.
- [x] Ghi phiên bản runtime, image digest, canonical hash và CLI được sử dụng thực tế.
- [x] Chưa sửa task, expected hoặc timeout để xử lý lỗi hạ tầng.
- [x] Tách ba loại việc: lỗi môi trường, lỗi công cụ đánh giá và lỗi hợp đồng task. Chỉ loại cuối mới cân nhắc thay task version.

**Bàn giao:** `reports/stage3-baseline-state.json` và tham chiếu tới archive/snapshot cũ. Không chạy lại toàn bộ 24 trial chỉ để xác nhận file còn tồn tại.

## 4. Q1 — Chẩn đoán Docker CLI qua WSL

**Câu hỏi cần trả lời**

1. Lệnh `docker` mà Harbor gọi là binary/script nào, nằm ở đâu, trỏ tới endpoint nào?
2. Engine không phản hồi, hay CLI/proxy/WSL subprocess không kết thúc/không đóng pipe?
3. Lỗi có phụ thuộc stdout/stderr capture, chạy trực tiếp, process con hoặc tải đồng thời không?
4. Có tiến trình probe cũ giữ tài nguyên/pipe, khác với lỗi daemon hay không?

**Đầu việc**

- [x] Thu có chọn lọc CLI path, loại executable, symlink, context/endpoint cần thiết và khả năng truy cập socket. Che thông tin nhạy cảm nếu có; không dump toàn bộ môi trường hoặc Docker credentials.
- [x] Đo cùng probe từ Windows, WSL trực tiếp và Python subprocess trong WSL, cùng timeout và chế độ capture được ghi rõ.
- [x] Nếu cần, dùng truy vấn chỉ đọc tới socket Linux để phân biệt API engine với CLI. API probe thành công không được dùng thay bằng chứng CLI Harbor hoạt động.
- [x] Ghi command đã làm sạch, thời điểm, elapsed time, exit code, stdout/stderr giới hạn kích thước và tình trạng process con.
- [x] Mọi probe có timeout và giới hạn tổng thời gian. Không dùng lệnh chờ vô hạn để tái hiện lỗi.
- [x] Chỉ dọn process thuộc probe/run này sau khi xác minh PID/quan hệ cha-con/command; không kill mọi `docker`, `python` hoặc `wsl`.
- [x] Thử sửa theo phạm vi hẹp: PATH/CLI Linux phù hợp, endpoint/context hoặc cách tạo/đóng subprocess. Không thay đổi cấu hình toàn máy trước khi có bằng chứng cần thiết.
- [x] Không tự restart Docker Desktop, shutdown WSL hoặc xóa cache/container của workload khác. Nếu chỉ còn cách ảnh hưởng dịch vụ chung, trình bày bằng chứng và phạm vi tác động cụ thể trước thao tác đó.

**Nghiệm thu:** ghi được nguyên nhân và bản sửa có thể tái lập; hoặc ghi rõ chưa xác định, dấu hiệu thu được và điều kiện tái hiện. Không viết “đã sửa” chỉ vì một lần probe tình cờ thành công.

**Bàn giao:** `scripts/diagnose_runtime.py`, `reports/runtime-diagnosis.md` và log JSON có thời gian. Tên file là dự kiến, chưa tồn tại từ kế hoạch này.

## 5. Q2 — Hoàn thiện preflight và giới hạn tiến trình

- [x] Mỗi bước preflight có tên, thời gian bắt đầu/kết thúc, trạng thái và lý do fail riêng; phân biệt filesystem, CLI, engine và policy.
- [x] Giữ timeout từng subprocess và bổ sung deadline tổng, trả nonzero khi không đạt.
- [x] Kiểm tra timeout không để lại process/proxy của probe giữ pipe; chỉ quản lý nhóm tiến trình do tác vụ tạo.
- [x] Xác nhận loại filesystem bằng phép thử case/NFC/NFD thực tế, không chỉ dựa vào tiền tố đường dẫn.
- [x] Xác nhận đúng Docker Linux, image/runtime đã khóa và Compose policy. Giữ verifier không mạng.
- [x] Không cho executor bắt đầu job khi preflight fail, thiếu manifest hoặc snapshot lệch.
- [x] Report dùng `ready=false` và lý do; không biến timeout môi trường thành model reward 0.
- [x] Test có mục tiêu cho CLI timeout, endpoint sai, output không hợp lệ, child process không thoát và đường dẫn có dấu/khoảng trắng.

**Ngưỡng development đề xuất:** mỗi probe CLI tối đa 10 giây, engine API tối đa 10 giây, preflight tổng tối đa 45 giây. Đây là ngưỡng kiểm tra hạ tầng, không phải timeout chấm model. Chốt hoặc điều chỉnh có lý do trước khi thực hiện, không tăng sau khi thấy kết quả để làm test pass.

**Nghiệm thu:** case tốt qua; case không đạt fail hữu hạn và có log; không tạo job hoặc model call khi guard fail. CLI mà Harbor thực sự dùng phải được kiểm tra, không chỉ một CLI thay thế.

## 6. Q3 — Điều tra latency verifier và smoke có mục tiêu

**Phân tích trước khi chạy thêm**

- [ ] Tách timestamps của build/start container, upload/download artifact, khởi động verifier, chạy grader và thu reward từ raw jobs hiện có.
- [x] Xem log B005/B006 repeat đầu, so với repeat 2/3 và no-op; tránh gán toàn bộ pha verifier thành thời gian grader.
- [ ] Kiểm tra tương quan với tải Docker, cạnh tranh build cùng image, WSL interop và trạng thái cache; giữ các giả thuyết tách khỏi kết luận.
- [x] Xác nhận timeout Harbor đang bao phủ pha nào; chưa sửa budget task chỉ để che thời gian setup/transfer.

**Thí nghiệm tối thiểu sau khi Q1/Q2 đạt**

- [x] Chọn B005 và B006, hai task từng có outlier.
- [x] Chạy hai điều kiện đã định nghĩa: lần đầu với bước build/start được ghi riêng và lượt dùng lại image đã build; mỗi trial vẫn dùng container sạch.
- [x] Tổng ban đầu: 2 task × 2 điều kiện = 4 oracle trial. Không xóa cache toàn cục để tạo “cold”; ghi chính xác mức cache thực tế.
- [x] Đo đơn luồng trước để cô lập lỗi; chỉ kiểm tra concurrency mục tiêu khi còn nghi vấn tải đồng thời.
- [x] Kiểm tra reward, checksum nguồn/artifact, tên Unicode và separate verifier như trước.
- [x] Dừng thí nghiệm khi preflight hoặc deadline thất bại, giữ log và đánh dấu lỗi hạ tầng; không retry vô hạn.

**Nghiệm thu:** không tái diễn treo vô hạn; các pha có thời gian đo được; nguyên nhân outlier được giải thích hoặc có giới hạn vận hành/điều kiện chưa biết được công bố. Bốn trial không chứng minh độ ổn định dài hạn; nếu còn outlier chưa giải quyết, giữ readiness chưa đạt cho pilot có phí.

Chỉ mở rộng kiểm định sang task khác khi có thay đổi runtime/harness hoặc lỗi liên quan. Oracle pass vẫn là kiểm định kỹ thuật, không phải phép đo hiểu lệnh EN/VI.

**Bàn giao:** `reports/runtime-stability.md`, raw smoke archive và quyết định ngưỡng vận hành trước pilot.

## 7. Q4 — Review độc lập và hiệu chỉnh task

- [x] Chuẩn bị gói review từ snapshot canonical, instruction EN/VI và hướng dẫn hiện có.
- [ ] Người phụ trách chỉ định reviewer khác tác giả; không tự điền tên/ngày/decision.
- [ ] Reviewer giải trước khi xem oracle/expected, ghi thời gian thực đo và điểm mơ hồ.
- [ ] Đối chiếu expected và ràng buộc EN/VI, đặc biệt mapping CP1258, tìm không dấu, collation và CSV nhiều dòng.
- [ ] Ghi `accepted` hoặc `changes_requested` đúng task hash; không tự chuyển pending thành accepted vì oracle pass.
- [ ] Nếu sửa nội dung chấm: tăng task version, changelog, materialize lại hai ngôn ngữ và kiểm định phần bị ảnh hưởng.
- [ ] Cập nhật độ khó bằng bằng chứng; giữ nhãn provisional nếu chỉ có ước lượng.

Có thể chuẩn bị gói review và sửa lỗi kỹ thuật đã biết trong lúc chờ reviewer. Không coi một lượt LLM tự review hoặc alternative solution cùng tác giả là thay thế người review độc lập. Không tự gửi tin nhắn/tài liệu ra ngoài khi chưa được chỉ dẫn.

**Nghiệm thu:** mỗi task đưa vào pilot chính thức có hồ sơ chấp nhận theo snapshot. Nếu thiếu reviewer, giữ scope development; không chặn việc hoàn thiện Q0–Q3 hoặc Q5 bằng lý do này.

## 8. Q5 — Model profile và dry-run không gọi API

**Thông tin cần từ người phụ trách**

| Nội dung | Cần chốt |
|---|---|
| Hai cấu hình | Agent/version, model ID cụ thể, provider, effort, system prompt và tool access |
| Ngân sách | Trần inference, compute, smoke riêng, concurrency và điều kiện dừng |
| Giới hạn | Token/turn/time theo profile; không đổi bất đối xứng EN–VI |
| Credentials | Cách cung cấp secret cho agent, không ghi repo hoặc chuyển vào verifier |
| Phạm vi | B-only 72 trial hoặc A+B khi đủ task/baseline |

Chưa có đầu vào thì chỉ tạo schema/template có trường thiếu rõ ràng. Không tự chọn model có phí hoặc coi thời gian chờ là đồng ý ngân sách.

**Thiết kế triển khai**

- [x] Giữ runner oracle/nop hiện tại là validation-only; model runner/profile phải có kiểu run riêng, không nới guard mặc định của công cụ kiểm định.
- [ ] Chọn agent ngoài sandbox điều khiển terminal qua harness, hoặc agent được chuẩn bị sẵn với đường API phù hợp. Chỉ chốt khi biết agent thực tế.
- [ ] Nếu cần mạng trong agent container, thiết kế và kiểm tra cách thực thi giới hạn mạng tương thích backend. Không tuyên bố allowlist được thực thi chỉ vì có field TOML.
- [x] Verifier giữ offline, không nhận API key, không chạy code submission với quyền grader.
- [x] Tạo cấu hình mẫu và dry-run manifest đầy đủ scope, planned trial ID, repeat, instruction/payload/config fingerprint và retry routing.
- [x] Manifest có danh sách expected configurations; thiếu toàn bộ config vẫn hiện trong coverage.
- [ ] Fingerprint và adapter so effective model/agent, prompt, kwargs, effort, endpoint, budget, resources và network profile cần thiết; không chỉ so tên model.
- [ ] Bổ sung test cho profile mới: cấu hình lệch, rate limit, provider error, timeout đúng budget, null reward, chi phí thiếu và retry. Unknown error không tự thành model fail.
- [x] Dry-run báo missing inputs, dự toán số trial và lệnh dự kiến; không tạo model call, không đọc/in secret để chứng minh cấu hình.

**Nghiệm thu:** có thể kiểm tra một cấu hình cụ thể trước chạy. Khi chưa có model/ngân sách, kết quả hợp lệ là template/dry-run báo chưa đủ đầu vào, không phải fake model result.

**Bàn giao:** `docs/model-run-profile.md`, template trong `configs/`, báo cáo `reports/model-pilot-dry-run.md`.

## 9. Q6 — Chuẩn bị dữ liệu test kín và cách diễn giải thống kê

- [x] Giữ sáu task hiện có là development; không chuyển task đã lộ thành private test chỉ bằng đổi tên hoặc con số.
- [x] Lập ma trận family cho task test mới, kiểm nguồn/quyền dùng và tránh chia cùng họ bài toán sang development/test.
- [x] Không thay đổi task đang pilot giữa các điều kiện; task mới thuộc snapshot/version khác.
- [x] Giữ CI B bằng null khi mỗi skill chỉ có một family. Hai family/skill chỉ là điều kiện tối thiểu của công cụ hiện tại, không bảo đảm CI đủ tin cậy cho xếp hạng.
- [x] Pilot sáu task dùng để chẩn đoán lỗi, độ khó, chi phí và phân biệt ngôn ngữ; không bắt mở rộng toàn bộ dataset trước khi chạy pilot chẩn đoán đã đủ điều kiện.
- [x] Công bố hạn chế cỡ mẫu, contamination và artifact-only; chưa tuyên bố năng lực viết chương trình tổng quát từ kết quả sáu task này.

**Bàn giao:** `docs/private-test-design.md` và backlog task theo family. Viết toàn bộ private set và phát hành license không nằm trong mặc định của giai đoạn ổn định hạ tầng này.

## 10. Q7 — Smoke model và native pilot khi đủ điều kiện

Chỉ thực hiện khi Q1–Q3 đạt, scope task đã review, model/profile/ngân sách được xác định và đường API được kiểm tra. Các đầu vào thiếu được trình bày bằng dry-run cụ thể từ Q5 trước khi cần quyết định của người phụ trách.

- [ ] Đóng băng task/config; ghi run ID, canonical hashes và provenance trước model call.
- [ ] Smoke model 1–2 trial theo ngân sách smoke riêng; xác nhận auth, tool calls, logs, artifact, reward và chi phí.
- [ ] Nếu smoke fail vì hạ tầng/profile, sửa đúng nguyên nhân và giữ attempt; không đưa vào pilot chính hoặc giả thành model fail.
- [ ] Lập native pilot: 6 task × 2 instruction × 3 repeat × 2 cấu hình = **72 trial**, chưa gồm smoke và retry hạ tầng.
- [ ] Trộn thứ tự chạy, cùng điều kiện giữa EN/VI, container sạch và không truyền lịch sử.
- [ ] Đặt trần chi phí và cơ chế dừng; khi vượt trần, lưu phần đã chạy và báo coverage thiếu. Không âm thầm giảm budget một phía.
- [ ] Lưu mọi attempt; tối đa hai retry bổ sung chỉ theo chính sách lỗi hạ tầng đã chốt, không chạy lại đáp án sai để lấy pass.
- [ ] Xuất raw/normalized results, điểm theo task/skill/language, delta theo điểm phần trăm, CI hoặc lý do không ước lượng được và chi phí có mẫu số rõ.
- [ ] Review lỗi task/verifier riêng với lỗi locale/agent; sửa task thì version hóa và đánh giá lại đối xứng các điều kiện bị ảnh hưởng.

**Nghiệm thu:** đủ 72 lượt hoặc ghi rõ phần thiếu; báo cáo là native pilot, không phải leaderboard phát hành. Không đưa oracle/nop/control vào model score.

**Bàn giao:** `reports/native-model-pilot.md`, run manifests, trial tables và archive Linux. Chưa thực hiện các đầu việc này khi model/ngân sách vẫn thiếu.

## 11. Q8 — Phần A khi có snapshot Eval

- [ ] Thu đầu vào theo [checklist Eval](../docs/eval-input-checklist.md), xác minh ref/hash/verifier và quyền dùng.
- [ ] Chọn sáu task phù hợp tài nguyên, dịch bốn biến thể, review và kiểm payload không đổi.
- [ ] Chốt baseline EN cũ có tương thích hay cần chạy lại; không so hai snapshot hoặc verifier khác nhau.
- [ ] Thêm 144 trial A để thành pilot A+B 216 trial; giữ A/B là hai phép đo riêng.

Thiếu nguồn A thì deferred; không dựng task mới rồi gắn nhãn bản dịch Terminal-Bench. Không chặn native pilot đã đủ điều kiện chỉ vì chưa có A. Tái sử dụng kết quả B chỉ khi snapshot và cấu hình trọng yếu không đổi.

## 12. Thứ tự, phụ thuộc và ước lượng

```text
Q0 → Q1 → Q2 → Q3 ─────────────┐
Q4 review khi có người ────────┤→ Q7 native pilot có điều kiện
Q5 template/dry-run → profile ─┘
Q6 thiết kế test kín: tiến hành độc lập, không là điều kiện bắt buộc của pilot chẩn đoán.
Q8 phần A: chờ nguồn Eval, không thay thế hoặc chặn phần B.
```

| Công việc | Ước lượng ngày làm việc | Phụ thuộc |
|---|---:|---|
| Bảo toàn bằng chứng, chẩn đoán CLI/endpoint | 1–2 | Hạ tầng truy cập được |
| Sửa guard/process và đo latency có mục tiêu | 1–2 | Kết quả Q1; có thể lâu hơn nếu lỗi WSL chưa tái hiện |
| Model template, dry-run và adapter profile | 1–2 | Phần template làm ngay; phần profile cụ thể chờ cấu hình |
| Hồ sơ review và thiết kế private test | 1 | Tài liệu chuẩn bị được; thời gian reviewer thực tế tách riêng |
| Smoke/pilot model, phần A | Ước lượng sau | Model/ngân sách/review/Eval và hiệu năng hạ tầng |

Ước lượng khoảng 4–7 ngày làm việc cho chuẩn bị kỹ thuật, không tính thời gian chờ đầu vào và không cam kết đã tìm ra lỗi runtime. Không nâng Harbor, Python hoặc image chỉ vì có phiên bản mới; thay đổi dependency cần lý do và kiểm định riêng.

## 13. Checklist bàn giao giai đoạn 3

- [x] Có báo cáo chẩn đoán và bằng chứng phân biệt API engine với CLI Harbor.
- [x] Preflight fail hữu hạn, không để lại probe của tác vụ và không cho chạy khi guard fail.
- [x] Đo được các pha setup/transfer/grade; smoke hạ tầng có mục tiêu giữ đúng reward/Unicode/cách ly.
- [x] Có quyết định runtime đủ điều kiện hoặc chưa đủ kèm lý do; không giả nhận đã hết lỗi.
- [ ] Có hồ sơ review theo snapshot; accepted chỉ khi người review thực sự xác nhận.
- [ ] Có model template, dry-run, run manifest và adapter/profile checks; phần thiếu model/ngân sách hiện rõ.
- [x] Có thiết kế private test theo family, không đổi development thành private giả.
- [ ] Chỉ khi thực sự chạy model: có báo cáo smoke/native pilot, coverage, chi phí và raw archive.
- [x] Phần A giữ deferred nếu chưa có nguồn; license/phát hành do chủ dự án quyết định.
- [x] Cập nhật kế hoạch và readiness theo bằng chứng mới, giữ nguyên báo cáo lịch sử.

**Việc triển khai đầu tiên:** Q0 và Q1, sau đó Q2; trong lúc chờ reviewer/model có thể hoàn thiện template Q5 và thiết kế Q6. Không mở rộng số lượng task để né lỗi runtime đang ngăn chạy ổn định.

## 14. Bằng chứng triển khai và phần chưa hoàn tất

- [Readiness giai đoạn3](../reports/stage3-readiness.md), [summary JSON](../reports/stage3-summary.json):41 test Linux và4 smoke oracle pass, không gọi model.
- [Chẩn đoán](../reports/runtime-diagnosis.md): default socket có lỗi/gián đoạn; proxy Desktop khỏe. Relay root chỉ mở socket riêng0600, command chạy user thường, không sửa config hoặc restart dịch vụ. Workaround đã kiểm định, chưa sửa triệt để default path.
- [Stability](../reports/runtime-stability.md):4 trial khoảng31–43 giây, phase verifier15–20 giây; chưa xác định nguyên nhân gốc outlier cũ, chưa có độ phân giải đầy đủ build/upload/grade hoặc concurrency2.
- [Dry-run model](../reports/model-pilot-dry-run.md):72 ID,27 trường thiếu,6 task pending review; không executable. Fingerprint helper không thay thế mapping real agent/Harbor.
- Gói review public/reference được ghi hash trong summary; không có reviewer hoặc accepted giả.
- Q7/Q8 chưa thực hiện. Phần mapping/profile và provider-specific tests ở Q5 chờ chọn agent/model; giữ checkbox chưa hoàn tất.
- Ngưỡng preflight là giới hạn hữu hạn cho subprocess và kiểm deadline giữa các bước I/O local, không bảo đảm hard real-time khi kernel I/O kẹt.
