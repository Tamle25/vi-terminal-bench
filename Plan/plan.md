# Kế hoạch tổng thể xây dựng benchmark terminal theo ngữ cảnh tiếng Việt

- Ngày lập: 12/11/2026.
- Trạng thái cập nhật 13/11/2026: **đã hoàn thành bản nhỏ development sáu task B** theo mục tiêu người dùng chốt ở giai đoạn 11: 36/36 trial model hợp lệ, 35 pass; EN 94,44%, VI 100%. Hồi quy 223/223 test Linux đạt; backend Docker thật, smoke thật, CLI/report/resume và restore archive đã kiểm. Token estimate bảo thủ cộng dồn khoảng 0,135 USD trong trần 2 USD, chưa invoice; compute local not-metered. Runtime explicit shared relay v2/pin controller CPU 0; review 0/6 pending, chưa phát hành chính thức hoặc hoàn thành phần A/pilot reviewed hai cấu hình. Xem [readiness hiện tại](../reports/stage11-readiness.md).
- Tên làm việc: Vietnamese Locale-aware Terminal Benchmark.
- Kế hoạch triển khai đầu tiên: [plan-giai-doan-dau.md](plan-giai-doan-dau.md).
- Kế hoạch tiếp theo sau M1: [plan-giai-doan-2.md](plan-giai-doan-2.md) — hoàn thiện sáu task B, công cụ và điều kiện pilot.
- Kế hoạch sau native-six: [plan-giai-doan-3.md](plan-giai-doan-3.md) — ổn định Docker/WSL, review và chuẩn bị model pilot có điều kiện.
- Kế hoạch tiếp theo: [plan-giai-doan-4.md](plan-giai-doan-4.md) — readiness gate, runtime profile và runner/ledger/retry/resume offline; model pilot khi đủ đầu vào.
- Kế hoạch sau runner offline: [plan-giai-doan-5.md](plan-giai-doan-5.md) — nối executor với gate/ledger, hoàn tất review và kiểm định adapter/runtime thực; smoke/pilot khi đủ đầu vào.
- Kế hoạch tiếp theo sau executor offline: [plan-giai-doan-6.md](plan-giai-doan-6.md) — ledger ngân sách chung, reconciliation và kết nối provider thực; review/runtime/smoke/pilot theo điều kiện đầu vào.
- Kế hoạch sau shared billing: [plan-giai-doan-7.md](plan-giai-doan-7.md) — chốt reviewer/cấu hình/budget, kiểm binding/runtime thực, chạy smoke rồi native pilot đầu tiên khi đủ điều kiện.
- Kế hoạch sau khi có credential OpenAI: [plan-giai-doan-8.md](plan-giai-doan-8.md) — nạp key cục bộ, kiểm binding OpenAI và nối billing/runtime thực; smoke/pilot theo model/budget được chọn.
- Kế hoạch sau credential loader: [plan-giai-doan-9.md](plan-giai-doan-9.md) — chốt run spec, kiểm kết nối provider có giới hạn, nối agent terminal và chạy smoke/pilot theo scope thực.
- Kế hoạch sau provider connectivity: [plan-giai-doan-10.md](plan-giai-doan-10.md) — host agent terminal, review B001, USD nhiều request và smoke EN/VI khi đủ gate; triển khai kỹ thuật một phần, chưa smoke thật.
- Mốc bản nhỏ theo mục tiêu mới: [plan-giai-doan-11.md](plan-giai-doan-11.md) — đã chạy đủ 36 trial nội bộ trên sáu task B, một cấu hình; cho phép review pending trong development, có CLI/report và evidence tái lập.

## 1. Mục tiêu và phạm vi

Xây dựng bộ benchmark đánh giá khả năng AI agent nhận yêu cầu, sử dụng terminal và hoàn thành công việc với dữ liệu, ngôn ngữ và quy ước Việt Nam. Chấm kết quả thực tế bằng verifier tự động, không chấm lời tự nhận hoàn thành của agent.

Đối tượng được đánh giá là cấu hình model + agent + công cụ + ngân sách. Kết quả phải đủ thông tin để tái lập và phân tích nguyên nhân thất bại.

Hai phần độc lập:

| Phần | Câu hỏi cần trả lời | Thiết kế |
|---|---|---|
| A — Ngôn ngữ yêu cầu | Agent có giảm hiệu quả khi nhận lệnh tiếng Việt? | Giữ task, dữ liệu, môi trường và verifier; chỉ thay instruction |
| B — Đặc thù Việt Nam | Agent có xử lý đúng dữ liệu và quy ước Việt Nam? | Task viết mới bởi kỹ sư Việt Nam, có tình huống thực tế và chấm tự động |

Phiên bản đầu công bố điểm A và B riêng. Không suy diễn điểm benchmark thành năng lực của model độc lập với agent hoặc thành năng lực trên mọi hệ điều hành.

## 2. Quy mô và các mốc phát hành

| Mốc | Phạm vi | Điều kiện chuyển mốc |
|---|---|---|
| M0 — Đặc tả | Chốt giao thức, nguồn task, phiên bản và cấu trúc repo | Đội xây dựng và đội Eval hiểu cùng một định nghĩa kết quả |
| M1 — Chạy xuyên suốt | 2 task B: hóa đơn và Unicode/tên file | Build, oracle, verifier, thu artifact và đọc kết quả hoạt động |
| M2 — Pilot | 6 task A × 4 instruction; 6 task B × 2 instruction | Task đã review; chạy thử; phân biệt lỗi agent, task và hạ tầng |
| M3 — Candidate | Hướng tới 66 task A và 30 task B | Nguồn task, tài nguyên và ngân sách đáp ứng; verifier đã kiểm định |
| M4 — v1.0 | Snapshot được đóng băng, báo cáo và dataset card | Kiểm tra phát hành đạt; kết quả tái lập được |

66 task A là mục tiêu khi sử dụng đầy đủ snapshot Terminal-Bench 4.0 tương ứng. Nếu chỉ sử dụng một phần, công bố rõ danh sách và không gọi kết quả là đánh giá toàn bộ 66 task.

## 3. Thiết kế phần A

Mỗi task gốc có bốn biến thể: `en`, `vi`, `vi_ascii`, `vi_mixed`.

1. Lấy snapshot tiếng Anh và cấu hình đánh giá từ đội Eval.
2. Ghi nguồn, phiên bản, commit/hash task, verifier và giấy phép.
3. Tạo bản dịch; kỹ sư Việt Nam review kỹ thuật; người khác đối chiếu ràng buộc.
4. Giữ nguyên identifier, tên API, trường dữ liệu, đường dẫn và code khi cần.
5. Bản không dấu chỉ thay văn bản chỉ dẫn; không tự động biến đổi dữ liệu hoặc đường dẫn.
6. Sinh các bản chạy từ một nguồn task chung và kiểm tra rằng chỉ instruction thay đổi.
7. Chạy các điều kiện độc lập, cùng ngân sách và cùng chính sách xử lý lỗi.

Nếu tài liệu bên trong môi trường vẫn là tiếng Anh, mô tả đây là phép đo ngôn ngữ instruction. Việt hóa toàn bộ tài liệu là thí nghiệm khác.

Baseline tiếng Anh có sẵn chỉ sử dụng khi phiên bản task, verifier, model, agent và điều kiện đánh giá tương thích. Nếu không xác minh được, chạy lại baseline. Không thay verifier một phía khi so sánh EN–VI.

## 4. Thiết kế phần B

Phân bổ ban đầu: 30 task gốc, chia đều sáu nhóm. Đây là mục tiêu thiết kế, có thể điều chỉnh sau pilot nhưng phải ghi lại lý do.

| Nhóm | Ví dụ | Số task mục tiêu |
|---|---|---:|
| Unicode và tên file | NFC/NFD, đường dẫn có dấu, va chạm khi đổi tên | 5 |
| Chuyển bảng mã | Windows-1258, TCVN3, VNI sang UTF-8 | 5 |
| Tìm kiếm và chuẩn hóa | Tìm không dấu, xử lý đ/Đ, slug và trùng slug | 5 |
| Sắp xếp và đối chiếu | Collation tiếng Việt, ghép danh mục, quy tắc bằng nhau | 5 |
| Số, tiền, ngày giờ | Dấu phân nhóm/thập phân, dd/mm/yyyy, ngày Việt Nam | 5 |
| CSV, log và pipeline | BOM, quote CSV, log tiếng Việt, sửa quy trình xuất | 5 |

Mỗi task có một năng lực chính, nhãn phụ, họ task, độ khó và ước lượng thời gian chuyên gia giải. Độ khó đến từ công việc và số ràng buộc cần phối hợp, không đến từ instruction mơ hồ.

Mỗi task B có instruction Việt và Anh tương đương, giữ dữ liệu Việt Nam để phân biệt tác động của ngôn ngữ yêu cầu và dữ liệu locale.

Quy tắc phải xác định: Unicode đầu ra, ánh xạ đ/Đ, kiểu tìm kiếm, thứ tự sắp xếp, xử lý tên trùng, ngày sai, số âm, làm tròn, dấu phân cách CSV, BOM, quote và xuống dòng. Không yêu cầu đoán bảng mã chính xác từ đầu vào không đủ thông tin.

## 5. Kiến trúc và tổ chức repository

Dùng Harbor làm harness. Môi trường đánh giá đầu tiên là Linux container; trên Windows ưu tiên phát triển qua WSL2 và Docker Linux. Chốt phiên bản Harbor trước khi viết cấu hình hàng loạt.

```text
Plan/                          # Kế hoạch và nhật ký quyết định
docs/                          # Đặc tả, hướng dẫn viết/review/chạy task
manifest.jsonl                 # Metadata, nguồn, họ task, phiên bản
prompts/<task-id>/              # Các biến thể instruction
tasks/<task-id>/
  instruction.md
  task.toml
  environment/Dockerfile
  environment/data/
  solution/solve.sh
  tests/Dockerfile
  tests/test.sh
  tests/grader.py
scripts/                       # Sinh biến thể, kiểm tra, tổng hợp điểm
configs/                       # Cấu hình chạy được version control
jobs/                          # Log và kết quả cục bộ; không commit mặc định
reports/                       # Báo cáo pilot và phát hành
THIRD_PARTY_NOTICES.md
```

Chỉ copy dữ liệu cần thiết vào agent image. Không đưa oracle, hidden tests hoặc đáp án vào build context được agent sử dụng. Sinh fixture tên file Unicode trong Linux container để hạn chế biến đổi khi đi qua hệ thống file máy chủ.

Chốt image digest, package lock, phiên bản Unicode/ICU, locale, timezone và seed khi áp dụng. Các task cố ý thay đổi locale phải mô tả điều kiện riêng. Không ghi API key vào repo hoặc log công khai.

## 6. Vòng đời và kiểm định từng task

1. Viết task card: mục tiêu, công việc, giao diện đầu vào/đầu ra, điều kiện đạt, lỗi cần bắt.
2. Tạo fixture tổng hợp có nguồn rõ ràng; kiểm tra byte/code point cho dữ liệu nhạy Unicode.
3. Viết verifier và oracle; đối chiếu một phần đáp án độc lập bằng tay.
4. Chạy oracle trong môi trường sạch ít nhất 3 lần; tất cả phải pass.
5. Chạy no-op và lời giải sai tiêu biểu; chúng phải fail đúng lý do.
6. Kiểm tra ít nhất một cách giải khác hợp lệ để tránh chấm theo implementation.
7. Người duyệt khác tác giả đọc instruction và giải/đối chiếu task.
8. Kiểm tra rò rỉ dữ liệu chấm, quyền truy cập và artifact transfer.
9. Khóa phiên bản; mọi sửa đổi sau đó có changelog và quyết định chấm lại.

Verifier kiểm tra nội dung, kiểu dữ liệu và hành vi được yêu cầu. Không ép thư viện, cách viết code hoặc thứ tự key JSON nếu instruction không yêu cầu. Với task đòi hỏi chương trình tổng quát, dùng dữ liệu kiểm tra riêng trong đúng phạm vi giao diện đã công bố.

Reward chính là 0/1. Lưu kết quả các nhóm kiểm tra để chẩn đoán; không tự thay đổi thang điểm sau khi xem điểm model.

## 7. Cách ly verifier và chống can thiệp kết quả

- Ưu tiên verifier container riêng; khai báo rõ artifact cần chuyển.
- Không coi container riêng là đủ nếu verifier chạy code do agent viết với quyền truy cập test và reward.
- Chạy code không tin cậy bằng worker/user bị giới hạn; grader tin cậy kiểm tra đầu ra và ghi điểm.
- Kiểm tra thiếu artifact, symlink và đường dẫn bất thường; giới hạn thời gian/kích thước đầu ra.
- Cài dependency khi build; tránh cài qua mạng ở giai đoạn chấm.
- Lưu artifact và phiên bản verifier để có thể chấm lại khi sửa lỗi.

## 8. Giao thức thực nghiệm

Mặc định chạy 3 lần độc lập cho mỗi task, biến thể instruction và cấu hình agent/model. Mỗi trial có môi trường sạch; không chia sẻ lịch sử hoặc kết quả giữa các điều kiện. Trộn thứ tự chạy để giảm ảnh hưởng thời điểm và tải dịch vụ.

Lưu: task/hash, instruction/hash, model định danh cụ thể, agent/version, system prompt, công cụ, ngân sách, timeout, CPU/RAM, image digest, chính sách mạng, Harbor/version, ngày chạy, reward, lỗi, token, thời gian và chi phí nếu thu thập được.

Phân biệt thất bại task với lỗi hạ tầng. Quy định retry, phân loại timeout và giới hạn lỗi trước khi chạy. Không chạy lại chỉ vì agent trả lời sai; mọi lần thử và lý do retry phải được giữ lại.

Trước khi chạy đầy đủ phần A, kiểm tra các task cần GPU, nhiều container hoặc tài nguyên lớn trong snapshot đã chọn; không giả định toàn bộ dataset chạy được trên laptop.

## 9. Chỉ số và báo cáo

Với N task và R lần chạy, điểm từng điều kiện là trung bình trên task của tỷ lệ pass qua R lần chạy:

```text
score(language) = mean_task(mean_repeat(reward))
delta_vi_pp = 100 * (score(vi) - score(en))
```

- Báo cáo A theo bốn biến thể và chênh lệch EN–VI theo điểm phần trăm.
- Báo cáo B theo sáu nhóm; điểm tổng đề xuất là trung bình đều các nhóm.
- Không gọi “ít nhất một lần pass trong ba lần” là pass@1.
- Tính khoảng tin cậy bằng bootstrap theo task/họ task; lấy mẫu cặp tương ứng khi so EN–VI.
- Không coi các bản dịch hoặc các lần chạy của cùng task là các task độc lập.
- Báo cáo số lỗi hạ tầng, số trial chưa đánh giá được và mẫu số dùng tính điểm.
- Phân tích lỗi theo Unicode, encoding, tìm kiếm, collation, số/ngày, hiểu lệnh, công cụ và hạ tầng.

Pilot dùng để kiểm tra phương pháp; không đưa kết luận mạnh về thứ hạng từ mẫu nhỏ.

## 10. Split, nguồn dữ liệu và quản lý phát hành

Đề xuất phần B: 10 task development công khai, 20 task test giữ kín. Chia theo họ bài toán; không để hai bản đổi tên/đổi số của cùng mẫu rơi vào hai split. Ghi rõ hạn chế học thuộc đối với phần A kế thừa từ task công khai.

Mỗi task có tác giả, reviewer, nguồn, giấy phép hoặc trạng thái quyền sử dụng, lịch sử sửa và hash. Terminal-Bench-LILT được tham khảo phương pháp; chưa đưa nội dung task mẫu vào dataset khi chưa xác minh quyền tái sử dụng.

Gói phát hành gồm dataset card, danh sách task, nguồn và attribution, hướng dẫn tái lập, cấu hình mẫu, schema kết quả, báo cáo baseline và hạn chế. Không công bố hidden tests hoặc log chứa bí mật ngoài chủ đích phát hành.

## 11. Nhân sự, tiến độ và chi phí

Vai trò tối thiểu: người phụ trách benchmark, kỹ sư task/harness, reviewer Việt Nam độc lập và người phối hợp đội Eval. Một người có thể kiêm nhiệm, nhưng task phải có người duyệt khác tác giả trước phát hành.

| Giai đoạn | Thời gian ước lượng | Sản phẩm |
|---|---|---|
| Đặc tả | 1 tuần | Spec, protocol, quyết định baseline |
| Dựng mẫu | 1 tuần | 2 task chạy xuyên suốt |
| Pilot | 1–2 tuần | 12 task gốc, báo cáo chất lượng và chi phí |
| Mở rộng | 2–4 tuần | Candidate 66 A + 30 B nếu đủ nguồn lực |
| Đóng băng và đánh giá | 1–2 tuần | Snapshot, baseline và tài liệu phát hành |

Đây là ước lượng cho nhóm nhỏ, không phải cam kết tiến độ. Điều chỉnh sau pilot.

| Phạm vi | Trial mỗi cấu hình | Hai cấu hình |
|---|---:|---:|
| Pilot: 6 A × 4 × 3 + 6 B × 2 × 3 | 108 | 216 |
| Đầy đủ: 66 A × 4 × 3 + 30 B × 2 × 3 | 972 | 1.944 |

Các số trên chưa gồm kiểm định task và retry hạ tầng. Ước lượng ngân sách từ pilot: chi phí inference + compute + lưu trữ + nhân công viết/review; xem cả trung bình và các trial đắt nhất.

## 12. Rủi ro và cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| Baseline EN không tương thích | Thu cấu hình từ Eval; chạy lại nếu không xác nhận được |
| Bản dịch thay đổi độ khó | Review ràng buộc và kiểm tra diff ngoài instruction |
| Chấm sai hoặc lọt lời giải sai | Oracle, negative controls, cách giải khác và review độc lập |
| Locale/encoding phụ thuộc máy | Pin môi trường; kiểm tra bytes; sinh fixture trong container |
| Trùng họ task giữa split | Gắn family_id và duyệt split trước phát hành |
| Điểm phản ánh lỗi hạ tầng | Phân loại lỗi, retry có quy tắc, lưu trial đầy đủ |
| Chi phí vượt dự kiến | Smoke test, pilot, đo chi phí trước khi mở rộng |
| Học thuộc task công khai | Công bố giới hạn; bổ sung task B viết mới và test kín |

## 13. Điều kiện nghiệm thu v1.0

- [ ] Mục tiêu, phạm vi và giao thức đã được duyệt và version control.
- [ ] Mỗi task có đặc tả rõ, nguồn rõ, oracle và verifier được kiểm định.
- [ ] Tất cả task phát hành có reviewer độc lập.
- [ ] Các biến thể A giữ nguyên thành phần ngoài instruction.
- [ ] Baseline EN tương thích hoặc được chạy lại.
- [ ] Môi trường và cấu hình chạy được cố định, artifact đủ để điều tra/chấm lại.
- [ ] Không còn lỗi nghiêm trọng trong task hoặc verifier.
- [ ] Báo cáo có điểm, độ bất định, lỗi hạ tầng, chi phí và hạn chế.
- [ ] Có thể tái lập một tập smoke test theo tài liệu trên môi trường sạch.

## 14. Tài liệu tham chiếu

Các nguồn đã được đối chiếu trong bước tư vấn ngày 12/11/2026; kiểm tra lại schema và phiên bản khi triển khai:

- [Terminal-Bench 4.0](https://www.tbench.ai/news/terminal-bench-4-0)
- [Terminal-Bench 4.1 và cải tiến verifier](https://www.tbench.ai/news/terminal-bench-4-1)
- [Repository Terminal-Bench](https://github.com/harbor-framework/terminal-bench)
- [Terminal-Bench-LILT](https://github.com/lilt/terminal-bench-lilt)
- [Harbor: task format](https://docs.harborframework.com/tasks/overview)
- [Harbor: configuration](https://docs.harborframework.com/tasks/configuration)
- [Harbor: separate verifier](https://docs.harborframework.com/tasks/separate-verifier)
- [Harbor: artifacts](https://docs.harborframework.com/tasks/artifacts)
- [Harbor: chạy job](https://docs.harborframework.com/jobs/run-a-job)
- [ICU Collation](https://unicode-org.github.io/icu/userguide/collation/)
- [Python unicodedata](https://docs.python.org/3/library/unicodedata.html)
