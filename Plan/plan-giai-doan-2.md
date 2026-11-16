# Kế hoạch giai đoạn 2 — Hoàn thiện sáu task bản địa và chuẩn bị pilot

- Ngày lập: 12/11/2026.
- Kế hoạch tiếp nối: [plan-giai-doan-3.md](plan-giai-doan-3.md), đã triển khai scoped workaround, smoke và dry-run; default WSL/review/model pilot còn phần chờ.
- Trạng thái cập nhật 12/11/2026: đã triển khai phần kỹ thuật P1–P6 và hồ sơ P0; native-six đạt 18/18 oracle, 6/6 nop đúng kỳ vọng, 125 controls và 27 test. Review độc lập, điều tra latency và model pilot còn chờ.
- Kế thừa: [kế hoạch giai đoạn đầu](plan-giai-doan-dau.md), [báo cáo M1](../reports/initial-validation.md).
- Mục tiêu gần nhất: sáu task B có thể kiểm định xuyên suốt, công cụ hỗ trợ đủ sáu task và kết quả chấm có thể đối chiếu.
- Mục tiêu có điều kiện: pilot B khi có model/ngân sách và review; pilot đầy đủ A+B khi có thêm task A và baseline tương thích.

## 1. Điểm xuất phát và phạm vi

Đã có hai task B (`b001-vn-invoice`, `b002-unicode-files`), instruction EN/VI, oracle và verifier riêng. M1 ghi nhận oracle Harbor 6/6 đạt, nop nhận reward 0 ở 2/2 trial, 45 verifier control và 9 unit test đạt. Đây là bằng chứng kiểm định kỹ thuật, chưa phải điểm model.

Hai bài học hạ tầng bắt buộc giữ:

1. Jobs và artifact nhạy tên file nằm trên filesystem Linux. Không chép cây artifact thô qua ổ Windows; sao lưu bằng tar và giải nén trên Linux.
2. Mạng tắt bằng Compose cho cấu hình oracle hiện tại. Trước model run phải thiết kế đường gọi API thực tế, không mặc định agent cài/chạy trong container offline sẽ hoạt động.

Giai đoạn này mở rộng bốn task B, review hai task cũ, hoàn thiện công cụ và chuẩn bị thực nghiệm. Không nhập task LILT chưa xác minh quyền sử dụng; không tự công bố giấy phép hoặc chạy model có phí khi chưa có cấu hình/ngân sách.

Thiếu baseline A không ngăn xây, kiểm định hoặc chuẩn bị pilot B. Review độc lập là điều kiện đưa task vào kết quả chính thức, không phải lý do dừng công việc triển khai có thể làm tiếp.

## 2. Mốc bàn giao

| Mốc | Sản phẩm | Điều kiện đạt |
|---|---|---|
| M1.1 — Công cụ mở rộng | Registry kiểm định, preflight, kiểm tra image theo manifest | Không còn giả định chỉ có hai task; regression M1 giữ nguyên kết quả |
| M1.2 — Native-six | B001–B006, mỗi task có EN/VI, oracle, grader và controls | Oracle 3/3, nop fail, alternative pass, mutants fail trên từng task |
| M1.3 — Pilot-ready | Adapter kết quả, run manifest, thống kê và hồ sơ review | Đối chiếu raw trial → dữ liệu chuẩn → bảng điểm được; ghi rõ phần chưa review |
| M2-B — Pilot bản địa | 6 B × 2 ngôn ngữ × 3 repeat × 2 cấu hình | Có model/ngân sách, review và cấu hình API phù hợp; đủ 72 trial |
| M2 — Pilot đầy đủ | 6 A × 4 ngôn ngữ và 6 B × 2 ngôn ngữ, mỗi loại 3 repeat, 2 cấu hình | Đủ đầu vào A và điều kiện M2-B; tổng 216 trial |

M2-B là một subset được công bố riêng; không gọi nó là pilot đầy đủ 12 task hoặc kết quả Terminal-Bench 66 task. Nếu chạy B trước, chỉ tái sử dụng kết quả cho M2 khi snapshot và mọi điều kiện trọng yếu giữ nguyên.

## 3. P0 — Giữ bằng chứng M1 và chuẩn bị review

**Đầu việc**

- [x] Kiểm tra archive M1 còn đọc được, đối chiếu reward/log/hash và thử giải nén vào thư mục Linux mới.
- [x] Giữ báo cáo lỗi cũ làm bằng chứng hạ tầng; phân biệt với kết quả nghiệm thu cuối.
- [x] Tạo `docs/review-guide.md` và hồ sơ `reports/reviews/<task-id>.md`.
- [ ] Ghi reviewer, ngày, task hash, nhận xét, lỗi tìm thấy và quyết định chấp nhận hoặc sửa.
- [ ] Review B001: ngày mơ hồ, định dạng tiền, ưu tiên lỗi, schema, bảo toàn nguồn và expected tĩnh.
- [ ] Review B002: thứ tự code point, cặp NFC/NFD, phân biệt hoa/thường, collision, hash và byte nhị phân.
- [ ] Đo thời gian giải của reviewer; không dùng ước lượng hiện tại như số đã đo.
- [ ] Khi sửa task đã kiểm định, tăng version và lưu changelog; kiểm định lại các điều kiện bị ảnh hưởng.

**Nghiệm thu:** có hồ sơ review rõ trạng thái. Nếu chưa có người review, giữ `review_status=pending`; không tự gán người hoặc coi alternative solution do cùng phiên viết là review độc lập.

## 4. P1 — Mở rộng công cụ trước khi thêm task

Hiện một số công cụ có giả định chỉ hai task: `validate_controls.py` phân nhánh B001/còn lại; `check_agent_images.py` kiểm số lượng bằng 2; `check_isolation.py` chỉ nhận prefix B001/B002. Cần xử lý các điểm này trước khi công cụ chạy trên B003–B006.

**Đầu việc**

- [x] Tạo registry development theo task ID cho fixture generator, oracle, alternative và controls; thiếu đăng ký phải báo lỗi rõ.
- [x] Registry chỉ chạy code tin cậy của tác giả trong quá trình kiểm định, không trở thành cơ chế import code submission trong verifier.
- [x] `validate_controls.py`: lấy danh sách từ manifest, không cho task mới rơi vào logic B002; hỗ trợ chọn task để kiểm định phần thay đổi.
- [x] `check_agent_images.py`: đối chiếu tập task/image theo manifest, không cố định số lượng; lỗi kiểm tra phải trả exit code khác 0.
- [x] `check_isolation.py`: nhận diện container theo run/project được chỉ định; không kiểm tra nhầm workload ngoài benchmark.
- [x] `validate_dataset.py`: kiểm tra file COPY, fixture/expected, schema, version, prompt và thiếu artifact theo cấu trúc từng task.
- [x] Kiểm tra wrapper với jobs-dir mặc định, đường dẫn Linux, đường dẫn Windows bị từ chối và đường dẫn có dấu/khoảng trắng.
- [x] Có preflight xác nhận loại filesystem của jobs, Docker Linux và chính sách mạng hiệu lực; fail rõ trước khi tính phí.
- [x] Giữ nguyên kết quả của các regression M1 trừ khi có thay đổi task được giải thích và version hóa.

**Nghiệm thu:** thêm task vào manifest nhưng thiếu controls sẽ bị phát hiện; không có pass giả do số lượng hoặc nhánh mặc định. Mỗi thay đổi công cụ chỉ thêm test cho hành vi có ảnh hưởng đến tính đúng của đánh giá.

## 5. P2 — Task B003: chuyển Windows-1258 sang UTF-8

- ID dự kiến: `b003-windows1258`; family `vn-legacy-encoding`; nhóm chính `encoding`.
- Công việc: chuyển tập văn bản có nhãn bảng mã nguồn rõ ràng sang UTF-8/NFC và lập báo cáo chuyển đổi.
- TCVN3/VNI để backlog cho đến khi xác minh mapping, fixture và quyền sử dụng; không giả định Python codec hỗ trợ sẵn mọi bảng mã.

**Hợp đồng phải chốt trước khi viết verifier**

- File metadata xác định encoding nguồn; không bắt đoán từ dữ liệu mơ hồ.
- Quy định cách đọc Windows-1258, xử lý combining marks, chuẩn hóa NFC, BOM, newline và bảo toàn dấu câu.
- Chọn hành vi khi gặp byte không hợp lệ: reject hoặc ghi lỗi theo giao diện; không âm thầm dùng replacement/ignore.
- Công bố schema báo cáo, tên đích, thứ tự, bảo toàn nguồn và giới hạn kích thước.

**Đầu việc**

- [x] Viết task card và instruction EN/VI tương đương.
- [x] Tạo fixture byte gốc trong container, có dấu tiếng Việt, đ/Đ, chuỗi tổ hợp và dấu câu; đối chiếu một mẫu bằng bảng mã độc lập/tài liệu nguồn.
- [x] Ghi expected Unicode và expected bytes riêng, không sinh đáp án trong grader bằng cùng pipeline oracle.
- [x] Viết oracle, alternative, grader dữ liệu và controls.
- [x] Controls bắt lỗi đọc nhầm UTF-8/Latin-1, mất combining marks, replacement, sai NFC/BOM, thiếu file và thay đổi nguồn.
- [x] Chạy oracle Harbor 3 lần, nop và cách giải khác; ghi provenance codec/Python/Unicode.

**Nghiệm thu:** dấu được giữ nguyên, mọi trường hợp lỗi đã công bố được xử lý đúng; không dùng “nhìn giống tiếng Việt” làm điều kiện chấm.

## 6. P3 — Task B004: tìm kiếm tiếng Việt không dấu

- ID dự kiến: `b004-accent-search`; family `vn-accent-search`; nhóm chính `search-normalization`.
- Công việc: tìm bản ghi phù hợp với tập truy vấn trong dữ liệu khách hàng giả, trả kết quả và thứ tự theo quy tắc xác định.

**Hợp đồng đề xuất**

NFD → loại combining marks → ánh xạ đ/Đ thành d/D → casefold. Chốt tìm chuỗi con hay toàn từ; đề xuất chuỗi con trên khóa chuẩn hóa, không tự xóa dấu câu hoặc gộp khoảng trắng nếu chưa yêu cầu. ID kết quả sắp theo thứ tự ASCII; giữ nguyên tên hiển thị có dấu. Nếu quy tắc cuối khác, cập nhật cả hai instruction trước tạo expected.

**Đầu việc**

- [x] Chốt trường được tìm, truy vấn rỗng, trùng truy vấn, thứ tự và định dạng kết quả rỗng.
- [x] Tạo fixture NFC/NFD, hoa/thường, đ/Đ, tên có/không dấu, punctuation và bản ghi dễ false positive.
- [x] Tạo expected match sets đối chiếu độc lập, bao gồm truy vấn không có kết quả.
- [x] Viết oracle, alternative, grader và controls: chỉ lowercase, bỏ sót đ, không xử lý NFD, tìm sai phạm vi, bỏ dấu tên hiển thị, thiếu/thừa ID và sai thứ tự.
- [x] Chạy kiểm định cục bộ và Harbor như B003.

**Nghiệm thu:** precision và recall đều đúng trên toàn bộ truy vấn; không pass nếu chỉ trả toàn bộ danh sách hoặc sửa tên hiển thị thành không dấu.

## 7. P4 — Task B005: sắp xếp theo collation tiếng Việt

- ID dự kiến: `b005-vietnamese-collation`; family `vn-collation`; nhóm chính `collation`.
- Công việc: sửa/xuất danh mục được sắp theo collation locale `vi`, không dùng thứ tự code point như B002.

**Hợp đồng phải chốt**

Chọn và ghi rõ ICU/CLDR version, locale chính xác, strength, normalization, case handling và numeric collation; công bố cách xử lý giá trị bằng nhau, ví dụ tie-break bằng ID ASCII. Fixture phải phân biệt được code point sort, bỏ dấu sort và locale sort. Không dùng thuật ngữ “sắp xếp tự nhiên” mà thiếu cấu hình.

**Đầu việc**

- [x] Xác minh tài liệu ICU và chọn bản phù hợp với môi trường hiện tại; khóa dependency/image, không tự nâng các task khác.
- [x] Cung cấp runtime/thư viện cần thiết trong agent image khi offline; không chấm khả năng tải package qua mạng.
- [x] Viết card, EN/VI và fixture gồm a/ă/â, d/đ, e/ê, o/ô/ơ, u/ư, dấu thanh, NFC/NFD và khóa bằng nhau.
- [x] Lập golden order tĩnh từ cấu hình đã chốt, kiểm tra độc lập; không yêu cầu agent dùng đúng một implementation nếu thứ tự đúng.
- [x] Viết grader, oracle và controls cho các kiểu sort sai, tie-break sai, mất bản ghi và thay đổi dấu.
- [x] Chạy oracle ba lần trên môi trường sạch; ghi ICU/CLDR thực tế vào provenance.

**Nghiệm thu:** task thể hiện được collation tiếng Việt; đáp án không phụ thuộc locale mặc định của máy người chạy.

## 8. P5 — Task B006: sửa pipeline xuất CSV tiếng Việt

- ID dự kiến: `b006-vietnamese-csv-export`; family `vn-csv-export`; nhóm chính `csv-log-pipeline`.
- Công việc: sửa một pipeline xuất CSV lỗi để tạo artifact đúng hợp đồng nhập của ứng dụng bảng tính mục tiêu.
- Phạm vi đầu tiên tập trung CSV; log tiếng Việt là nhãn phụ khi có yêu cầu cụ thể, không gom thêm nhiều mục tiêu làm mơ hồ task.

**Hợp đồng đề xuất**

UTF-8 có đúng một BOM đầu file; delimiter, quote, CRLF, thứ tự cột, số tiền/ngày và công thức dữ liệu phải được chốt cụ thể. Có fixture chứa dấu phẩy, dấu chấm phẩy, quote và xuống dòng trong ô. Chỉ tuyên bố đúng hợp đồng CSV được kiểm thử; không khẳng định đã thử mọi phiên bản/cấu hình Excel.

**Đầu việc**

- [x] Chọn artifact-only hoặc yêu cầu sửa chương trình có CLI rõ; ghi quyết định vào task card trước triển khai.
- [x] Ưu tiên artifact-only nếu chưa cần chạy submission; vẫn có thể cung cấp source pipeline lỗi cho agent sửa để tạo output.
- [ ] Nếu yêu cầu chương trình tổng quát, công bố CLI và phạm vi input, bổ sung worker giới hạn quyền trước khi chạy code agent trong verifier. Không áp dụng cho artifact-only hiện tại; chưa triển khai worker chạy submission.
- [x] Viết EN/VI, fixture, expected cells và các điều kiện byte bắt buộc.
- [x] Grader kiểm tra BOM/newline/schema và parse CSV; không so byte ở những phần instruction cho phép nhiều cách biểu diễn.
- [x] Controls bắt thiếu/lặp BOM, sai delimiter, dùng split đơn giản, quote sai, mất dấu, hỏng ô nhiều dòng và sai thứ tự cột.
- [x] Oracle 3/3, nop fail, alternative pass và mutants fail.

**Nghiệm thu:** sửa được quy trình xuất và bảo toàn giá trị từng ô; verifier không đánh đồng CSV có BOM với khả năng tương thích mọi thiết lập bảng tính.

## 9. P6 — Hoàn thiện chuỗi dữ liệu kết quả

**Adapter Harbor → JSONL chuẩn hóa**

- [x] Tạo `scripts/import_harbor_results.py` cho phiên bản Harbor đã khóa, có schema mapping được mô tả.
- [x] Tạo run manifest trước khi chạy: planned trial ID, task/family, language, config, repeat, snapshot hash và retry mapping. Không đoán repeat từ thứ tự thư mục khi đã có retry.
- [x] Lưu raw job/trial reference và log phân loại; không bỏ trial lỗi hoặc thay null bằng 0.
- [x] Map completed, agent_timeout, agent_error, infra_error và verifier_error theo giao thức; trường hợp chưa biết phải yêu cầu phân loại, không mặc định model fail.
- [x] Giữ mọi attempt; retry chỉ sau lỗi hạ tầng/verifier, không chọn reward cao nhất.
- [x] Reward Harbor dạng 0.0/1.0 được chuyển có kiểm tra sang integer; từ chối NaN, giá trị ngoài miền và reward thiếu khi completed.
- [x] Đối chiếu adapter bằng raw jobs M1 đã có, fixture lỗi và retry; không cần gọi model để kiểm thử mapping.

**Coverage và thống kê**

- [x] Bổ sung expected configurations từ run manifest để phát hiện cả cấu hình không có trial nào; không chỉ kiểm tra cấu hình xuất hiện trong input.
- [x] Kiểm tra duplicate/gap, task/language thiếu, unresolved errors, chi phí từng attempt và task cùng snapshot.
- [x] Giữ macro-average theo task; B macro-average theo nhóm; A và B tách riêng.
- [x] Thêm CI bootstrap 95% theo family, seed cố định và paired resampling khi so EN–VI; không coi repeat/bản dịch là task độc lập.
- [x] Quy định cách báo cáo khi thiếu dữ liệu và số family nhỏ; pilot sáu task B không đủ để tuyên bố thứ hạng chắc chắn.
- [x] Kiểm tra bằng dữ liệu biết trước: toàn pass/fail, retry, kết quả không cân bằng, thiếu cả config và cặp EN–VI không khớp.

**Nghiệm thu:** truy vết được một dòng bảng điểm về raw attempt; điểm thiếu coverage phải provisional và không tạo chênh lệch ngôn ngữ sai mẫu số.

## 10. P7 — Chuẩn bị phần A khi có đầu vào

- [ ] Thu snapshot, config và provenance theo [checklist Eval](../docs/eval-input-checklist.md); ghi cái nào đã có và còn thiếu.
- [ ] Kiểm tra giấy phép, NOTICE, dependencies, CPU/GPU/multi-container; chọn sáu task pilot phù hợp tài nguyên.
- [ ] Chốt dùng baseline cũ hay chạy lại EN; không so snapshot/verifier khác phiên bản.
- [ ] Tạo bốn instruction EN/VI/VI không dấu/Anh–Việt; giữ nguyên code, path, identifier và dữ liệu.
- [ ] Review ràng buộc và thuật ngữ; check hash payload giữa các biến thể.
- [ ] Thêm task A vào registry, manifest và công cụ mà không giả định mọi task A dùng fixture generator của task B.
- [ ] Kiểm định theo cấu trúc và tài nguyên task A thực tế; không áp đặt timeout 300 giây của development B lên task gốc.

Nếu chưa có nguồn A, ghi trạng thái deferred và tiếp tục P0–P6. Không tạo task gốc thay thế rồi gọi là bản dịch Terminal-Bench.

## 11. P8 — Chuẩn bị và chạy pilot có điều kiện

**Đầu vào cần có trước model run**

- Reviewer độc lập xác nhận task thuộc phạm vi chạy; nếu thiếu, chỉ chạy development experiment với nhãn rõ khi người phụ trách đã chọn phạm vi đó.
- Hai cấu hình model/agent cụ thể, giới hạn inference/compute, credentials và chính sách log.
- Agent/API hoạt động với mô hình mạng đã chọn. Giữ verifier offline; không mount secret vào grader hoặc đưa secret vào artifact.
- Snapshot, run manifest, retry policy, seed/thứ tự và ngân sách được ghi trước khi chạy.

**Đầu việc**

- [ ] Chạy smoke test 1–2 trial có model để xác minh auth, tool calls, artifact, grader, token và chi phí; đây là chi phí riêng ngoài pilot.
- [ ] Kiểm tra semantic EN/VI và coverage; đóng băng task trước lượt đo chính.
- [ ] Với B-only: 6 × 2 × 3 × 2 = 72 trial; nhãn `native-pilot`.
- [ ] Với A+B: phần A 144, phần B 72, tổng 216 trial; nhãn `full-pilot`.
- [ ] Dự toán từ smoke test và đặt trần chi phí; trial timeout/output budget và concurrency có cấu hình rõ.
- [ ] Khi chạm trần hoặc lỗi hệ thống lặp lại, ghi trial còn thiếu và giữ kết quả provisional; không âm thầm hạ ngân sách giữa EN–VI.
- [ ] Thu mọi raw attempt, normalized records, artifact và báo cáo coverage; sao lưu tar trước dọn runtime.
- [ ] Phân tích lỗi task/verifier/hạ tầng riêng với lỗi locale của agent; tăng version và chấm/chạy lại đối xứng nếu sửa task.

**Nghiệm thu:** đủ số trial theo scope đã công bố hoặc báo rõ phần thiếu; báo cáo điểm, CI có giới hạn, chi phí và cấu hình; không phát hành leaderboard từ dữ liệu development chưa review.

## 12. Kiểm định kỹ thuật và số lượt dự kiến

Tối thiểu cho sáu task B ở giai đoạn native-six: 18 oracle trial (3/task) và 6 nop trial qua Harbor, cộng controls cục bộ và alternative mỗi task. Nếu chạy lại cùng kiểm định trên cả EN/VI thì số lượt tương ứng là 36 oracle và 12 nop; ghi rõ điều kiện thực tế, không bắt buộc nhân đôi chỉ vì oracle không đọc instruction.

Oracle và nop kiểm tra pipeline; hash payload cùng review nội dung mới kiểm tra tính tương đương bản dịch. Không dùng oracle pass để suy ra agent hiểu instruction Việt/Anh.

Chỉ chạy lại regression khi thay đổi/failure liên quan; tái sử dụng bằng chứng cũ nếu hash và môi trường tương thích. Không lặp kiểm định rộng khi chưa có thay đổi hoặc rủi ro chưa giải quyết.

## 13. Thứ tự ưu tiên và thời gian

| Ưu tiên | Công việc | Ước lượng ngày làm việc | Phụ thuộc |
|---|---|---:|---|
| 1 | P0 hồ sơ review và P1 công cụ | 1–2 | M1 hiện có |
| 2 | P2 B003 encoding | 1–2 | Registry/preflight |
| 3 | P3 B004 search | 1–2 | Registry/preflight |
| 4 | P4 B005 collation | 2–3 | Chốt ICU/CLDR và fixture |
| 5 | P5 B006 CSV | 1–2 | Chốt hợp đồng và cách chấm |
| 6 | P6 adapter/thống kê, hồi quy native-six | 2–3 | Có task và raw trial đại diện |
| Có điều kiện | P7 task A, P8 model pilot | Ước lượng sau khi đủ đầu vào | Eval, review, model/ngân sách |

Ước lượng 8–14 ngày làm việc cho phần kỹ thuật P0–P6, chưa tính thời gian chờ reviewer và đầu vào bên ngoài. Điều chỉnh sau B003/B004; không bỏ kiểm định để giữ lịch. Không tự liên hệ reviewer/Eval hay gửi tài liệu ra ngoài từ kế hoạch này.

## 14. Sản phẩm bàn giao và Definition of Done

- [x] Bốn task mới trong `tasks/`, EN/VI trong `prompts/`, metadata/version/changelog đầy đủ.
- [x] Registry kiểm định và công cụ không còn giả định chỉ hai task.
- [x] Mỗi task có golden data, oracle, alternative, negative controls và trạng thái review trung thực.
- [x] Native-six qua cấu trúc/schema, oracle, nop và controls theo phạm vi đã ghi.
- [x] Có run manifest, adapter chuẩn hóa, coverage và CI được kiểm tra bằng dữ liệu biết trước.
- [x] Có báo cáo `reports/native-six-validation.md` và `reports/pilot-readiness.md` ghi bằng chứng, lỗi, chi phí compute và điều kiện còn thiếu.
- [x] Task A và model run giữ trạng thái chờ nếu thiếu đầu vào, không đánh dấu hoàn thành từ native-six.
- [ ] Khi thực sự chạy pilot, có báo cáo `reports/pilot-report.md`, raw archive và cấu hình tái lập.
- [x] Cập nhật kế hoạch tổng thể và checklist giai đoạn đầu theo kết quả thật, không đánh dấu trước.

**Đầu việc bắt đầu ngay khi triển khai kế hoạch này:** P1 tách registry theo task và loại bỏ các giả định hai task, chuẩn bị hồ sơ review P0, sau đó xây B003 và B004. Các việc này không phụ thuộc baseline A hoặc model có phí.

## 15. Bằng chứng và phần việc còn mở

- [Kiểm định native-six](../reports/native-six-validation.md): 24 raw trial được archive và khôi phục, expected artifacts đúng, không có điểm model.
- [Điều kiện pilot](../reports/pilot-readiness.md): chưa đủ reviewer, model/ngân sách, đường API và đầu vào A; có hai outlier pha verifier cần điều tra.
- [Hồ sơ review](../docs/review-guide.md) được chuẩn bị nhưng tất cả pending; không tự đánh dấu review con người hoàn tất.
- Payload ngoài instruction của cả sáu task EN/VI giống nhau; Harbor chạy scope VI để kiểm kỹ thuật, không đo năng lực ngôn ngữ.
- B005 khóa Node22.14.0/ICU76.1/CLDR46.0; B003 chỉ CP1258, chưa TCVN3/VNI.
- P7/P8 chưa chạy. Kế hoạch này chưa hoàn thành toàn bộ vì các điều kiện trên còn thiếu; có thể tiếp tục review, điều tra latency và chuẩn bị private split mà không gọi model có phí.
