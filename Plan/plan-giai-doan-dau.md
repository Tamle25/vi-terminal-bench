# Kế hoạch thực hiện những bước đầu tiên

- Ngày lập: 12/11/2026.
- Kế hoạch tổng thể: [plan.md](plan.md).
- Phạm vi: từ đặc tả đến 2 task chạy xuyên suốt, sau đó mở rộng pilot 12 task gốc.
- Trạng thái cập nhật 12/11/2026: đã triển khai mốc kỹ thuật M1 (hai task B, verifier và chạy Harbor). S7–S9 và review độc lập chưa hoàn thành.
- Bằng chứng: [báo cáo kiểm định ban đầu](../reports/initial-validation.md). Oracle qua Harbor đạt 6/6; nop nhận reward 0 ở 2/2 trial; 45 control và 9 unit test đạt.
- Kế hoạch tiếp nối: [plan-giai-doan-2.md](plan-giai-doan-2.md), đã triển khai native-six kỹ thuật và chuẩn hóa kết quả; review độc lập và pilot model còn chờ.

## 1. Kết quả cần đạt

Ưu tiên chứng minh pipeline hoạt động và chấm đúng trước khi sản xuất nhiều task. Mốc kỹ thuật đầu tiên:

```text
Instruction → agent trong container sạch → artifact
            → verifier độc lập → reward + log + báo cáo
```

Hai task đầu:

| ID dự kiến | Task | Năng lực chính |
|---|---|---|
| b001-vn-invoice | Chuẩn hóa hóa đơn Việt Nam | Số tiền, ngày tháng, Unicode và CSV |
| b002-unicode-files | Lập danh mục và xử lý tên file NFC/NFD | Unicode, đường dẫn có dấu, va chạm |

Chưa chạy đầy đủ 66 task A ở giai đoạn này. Việc thiếu snapshot hoặc cấu hình của đội Eval chỉ chặn phần so sánh A; vẫn tiếp tục xây task B và harness.

## 2. Thứ tự triển khai và phụ thuộc

```text
S1 Chốt đặc tả ──→ S2 Dựng môi trường ──→ S3 Chuẩn task
                                             │
                                             ▼
                                    S4 Task hóa đơn
                                             │
                                             ▼
                                    S5 Task Unicode
                                             │
                                             ▼
                                    S6 Kiểm định pipeline
                                             │
                                             ▼
                                    S8 Chạy pilot → S9 Review

S1 → S7 Thu nguồn A, dịch và xây đủ task pilot ──→ S8
```

Các việc không phụ thuộc snapshot A có thể tiến hành trong lúc thu thập thông tin từ Eval. Không liên hệ hoặc gửi dữ liệu ra ngoài khi chưa có chỉ dẫn tương ứng của người phụ trách.

## 3. S1 — Chốt đặc tả và quyết định ban đầu

**Đầu việc**

- [x] Tạo `docs/benchmark-spec.md`: mục tiêu A/B, đơn vị đánh giá, phạm vi Linux, quy mô pilot.
- [x] Tạo `docs/evaluation-protocol.md`: 3 lần chạy, ngân sách, phân loại lỗi, retry, cách tính điểm.
- [x] Tạo `docs/decisions.md`: quyết định, lý do, ngày và vấn đề còn mở.
- [x] Lập bảng năng lực sáu nhóm và phân bổ 6 task B của pilot.
- [x] Ghi yêu cầu cần lấy từ đội Eval: snapshot 4.0, task/verifier hash, agent/model/version, prompt, ngân sách, tài nguyên và kết quả từng trial nếu có.
- [ ] Kiểm tra nguồn, giấy phép và các phụ thuộc của task kế thừa; ghi nguồn tham khảo phương pháp LILT riêng.

**Mặc định triển khai đề xuất**

- Linux container; dữ liệu tự tạo, không dùng thông tin cá nhân thật.
- Reward chính 0/1; log chi tiết để phân tích.
- Task B có instruction Việt và Anh tương đương.
- Ba lần thử độc lập; mỗi lần dùng môi trường sạch.
- Không sử dụng điểm EN có sẵn trước khi xác nhận tính tương thích.

**Nghiệm thu:** có thể đọc tài liệu và xác định rõ một trial pass/fail nghĩa là gì, trường hợp nào là lỗi hạ tầng và hai kết quả nào được phép so sánh.

## 4. S2 — Dựng môi trường phát triển tối thiểu

**Đầu việc**

- [x] Kiểm tra trạng thái workspace, Git và hướng dẫn repository trước khi tạo code.
- [x] Kiểm tra WSL2, Docker Linux, tài nguyên khả dụng và kết nối daemon.
- [x] Cài/chọn phiên bản Harbor phù hợp; ghi version và tham chiếu schema tương ứng.
- [x] Tạo các thư mục `docs`, `tasks`, `prompts`, `scripts`, `configs`, `reports` khi bắt đầu triển khai.
- [x] Thêm quy tắc Git cho file script dùng LF; không commit secrets, cache, image hoặc `jobs/` mặc định.
- [x] Chốt base image và dependency; ghi image digest khi đóng băng.
- [x] Kiểm tra đọc/ghi UTF-8, tạo file có dấu và sinh cặp NFC/NFD bên trong container.
- [x] Tạo hướng dẫn chạy môi trường sạch trong `docs/development.md`.

Lệnh kiểm tra/cài đặt tham khảo trong WSL/Bash; xác nhận với phiên bản thực tế trước khi dùng:

```bash
docker version
docker info
uv tool install harbor
harbor --version
harbor run --help
```

Nếu Harbor đã được cài, kiểm tra phiên bản trước khi thay đổi. Không nâng phiên bản giữa các điều kiện của cùng đợt đánh giá.

**Nghiệm thu:** chạy được container Linux; phiên bản được ghi lại; UTF-8 và fixture Unicode đúng byte/code point; có hướng dẫn tái lập.

## 5. S3 — Chuẩn hóa task card, metadata và cách chấm

**Đầu việc**

- [x] Tạo `docs/task-authoring.md` và mẫu task card.
- [x] Định nghĩa manifest: `task_id`, `family_id`, `track`, `primary_skill`, `difficulty`, `task_version`, `source`, `license_status`, `author`, `reviewer`.
- [x] Tạo task Harbor tối thiểu theo đúng schema đã chốt; tránh sao chép cấu hình từ tài liệu phiên bản khác.
- [x] Chốt cách đặt đường dẫn đầu vào/đầu ra, giao diện CLI nếu có và artifact cần thu.
- [x] Cấu hình verifier riêng; xác minh file đầu ra được chuyển đúng đường dẫn.
- [x] Xác định cách bảo vệ test/reward nếu task thực thi code do agent tạo. Hai task đầu chỉ chấm dữ liệu, không thực thi submission.
- [x] Viết checklist review: rõ yêu cầu, đúng fixture, oracle, lời giải sai, cách giải khác và rò rỉ test.

Task card tối thiểu gồm:

```text
ID / họ task / nhóm năng lực / độ khó
Tình huống công việc và mục tiêu đo
Đầu vào và phạm vi dữ liệu hợp lệ
Đầu ra và điều kiện đạt
Quy tắc locale và xử lý trường hợp lỗi
Các lỗi phổ biến verifier cần phát hiện
Oracle, fixture, nguồn và reviewer
```

**Nghiệm thu:** có template dùng lại được và reviewer xác định được phần nào công khai cho agent, phần nào chỉ dành cho chấm.

## 6. S4 — Xây task b001-vn-invoice

**Hợp đồng task cần chốt**

- Đầu vào: CSV UTF-8, header và dấu phân cách được mô tả; tên khách hàng có thể ở NFC/NFD.
- Ngày: `dd/mm/yyyy`, kiểm tra ngày hợp lệ; đầu ra `yyyy-mm-dd`.
- Tiền: số nguyên VND không âm; số có phân nhóm dùng dấu chấm theo nhóm ba chữ số. Quy định rõ có chấp nhận dạng không phân nhóm hay không.
- Tên: bỏ khoảng trắng hai đầu và chuẩn hóa NFC, giữ nguyên dấu.
- Đầu ra: JSONL UTF-8 không BOM, schema và kiểu dữ liệu cố định; thứ tự theo invoice_id dạng chuỗi.
- Dòng lỗi: có số dòng và mã lỗi; quy định ưu tiên khi nhiều trường cùng sai.
- Phạm vi ID, quy tắc trùng ID và các cột thiếu/thừa phải được xác định trước khi chấm.
- Bản đầu là task tạo artifact từ dữ liệu đã cho; không bắt tổng quát hóa bằng hidden input nếu instruction không yêu cầu chương trình tổng quát.

**Đầu việc**

- [x] Viết task card và hai instruction EN/VI.
- [x] Sinh fixture đúng, lỗi và sát biên; giữ checksum nguồn để kiểm tra bảo toàn.
- [ ] Viết expected output và đối chiếu thủ công một tập đại diện. Expected tĩnh và alternative solution đã có; còn chờ người review độc lập.
- [x] Viết `grader.py`, `test.sh`, oracle và cấu hình Harbor.
- [x] Thu artifact output vào verifier riêng; kiểm tra encoding, schema và nội dung.
- [x] Chạy oracle ba lần trên môi trường mới.
- [x] Kiểm tra lời giải sai và cách giải hợp lệ khác.

Fixture bắt buộc: tên có Đ/ă/ơ/ư, NFC/NFD, tên chứa dấu phẩy được quote, khoảng trắng, `03/04/2026`, ngày nhuận hợp lệ/không hợp lệ, số 0, số tiền phân nhóm và định dạng sai.

Lời giải sai bắt buộc: file rỗng, chỉ dòng đầu, bỏ dấu, đảo ngày/tháng, sai số tiền, số tiền thành chuỗi, thiếu danh sách lỗi.

**Nghiệm thu:** oracle pass 3/3; tất cả negative controls fail; cách giải khác pass; không so sánh JSON theo khoảng trắng hoặc thứ tự key ngoài yêu cầu.

## 7. S5 — Xây task b002-unicode-files

**Hợp đồng task cần chốt**

- Fixture được tạo trong Linux container bằng script xác định trước, có tên NFC/NFD và khoảng trắng.
- Công việc: lập danh mục hoặc đổi tên theo quy tắc NFC đã công bố.
- Nếu đổi tên: quy tắc va chạm tên sau chuẩn hóa phải được ghi rõ; không mất hoặc ghi đè nội dung.
- Manifest kết quả phải cho biết tên gốc/tên đích và thông tin kiểm tra bảo toàn theo schema công bố.
- Không đồng nhất chuẩn hóa NFC với bỏ dấu.
- Giới hạn phạm vi loại file, thư mục con và symlink; chỉ kiểm tra trường hợp đã mô tả.

**Đầu việc**

- [x] Chọn cụ thể công việc và chốt thuật toán phân giải va chạm có tính xác định.
- [x] Viết instruction EN/VI, fixture generator và kiểm tra code point.
- [x] Viết oracle, verifier và khai báo artifact bao gồm dữ liệu cần kiểm tra bảo toàn.
- [x] Chạy negative controls: bỏ sót file NFD, mất file, ghi đè file, bỏ dấu tên file, xử lý sai khoảng trắng.
- [x] Chạy oracle 3 lần; thử một cách giải hợp lệ khác.

**Nghiệm thu:** verifier phát hiện mất/ghi đè dữ liệu và sai chuẩn hóa; task tái lập được trong container sạch, không phụ thuộc thao tác sao chép tên file trên Windows.

## 8. S6 — Kiểm định pipeline và tổng hợp kết quả

**Đầu việc**

- [x] Kiểm tra cấu trúc task, manifest, file tham chiếu và instruction tương ứng.
- [x] Chạy oracle và no-op bằng harness; giữ log/artifact đầy đủ trên filesystem Linux.
- [x] Xác minh thiếu artifact không được tính pass.
- [x] Kiểm tra image agent không chứa oracle/test/expected; verifier riêng không chạy submission và tự ghi reward. Chưa phải audit bảo mật toàn diện.
- [x] Viết `scripts/aggregate_results.py`, giữ trial gốc và phân loại lỗi riêng.
- [x] Có công cụ xuất bảng trial chuẩn hóa và CSV; chưa có bảng điểm model hoặc adapter tổng quát cho raw output Harbor.
- [x] So sánh tính điểm tự động với tập kết quả biết trước qua 9 unit test, gồm macro average và retry.
- [x] Viết `reports/initial-validation.md`: kết quả, lỗi tìm thấy, điều kiện còn thiếu.

**Nghiệm thu:** 2 task chạy được xuyên suốt; oracle đúng, lời giải sai bị loại; kết quả tổng hợp khớp trial gốc. Nếu chưa có thông tin xác thực model, vẫn hoàn thành kiểm định oracle/no-op và ghi rõ agent trial chưa chạy.

## 9. S7 — Chuẩn bị đủ pilot 12 task gốc

**Phần A: 6 task gốc**

- [ ] Xác minh snapshot và nguồn task; kiểm tra nhu cầu GPU/nhiều container trước khi chọn.
- [ ] Chọn 6 task đa dạng, trong tài nguyên hiện có; công bố đây là subset.
- [ ] Tạo bốn instruction: en, vi, vi_ascii, vi_mixed; giữ code/identifier/path.
- [ ] Review bản dịch và kiểm tra các ràng buộc tương đương.
- [ ] Viết script materialize variants và kiểm tra hash các thành phần ngoài instruction.
- [ ] Chốt sử dụng baseline cũ hay chạy lại EN dựa trên bằng chứng cấu hình.

**Phần B: 6 task gốc**

- [x] Hoàn thiện kỹ thuật hai task đầu và bốn task còn lại, mỗi nhóm có một task chính; review độc lập còn chờ.
- [x] Bổ sung CP1258 có nhãn nguồn, tìm không dấu, collation khóa ICU/CLDR và CSV; log là phạm vi tương lai.
- [ ] Mỗi task có EN/VI, oracle, negative controls và reviewer khác tác giả.
- [x] Gắn family_id để chuẩn bị chia split khi mở rộng.

**Nghiệm thu:** đủ 12 task gốc đã kiểm định; không tính các bản dịch là task gốc mới.

## 10. S8 — Chạy pilot có kiểm soát

Chọn 2 cấu hình agent/model có thể sử dụng với ngân sách được người phụ trách xác định. Trước đợt đầy đủ, chạy smoke test 1–2 trial để kiểm tra xác thực, artifact và log chi phí.

Lệnh mẫu trong WSL/Bash, thay placeholder bằng cấu hình thực tế và đối chiếu `--help` của phiên bản đã chốt:

```bash
harbor run \
  -p ./build/pilot-vi \
  -a "<agent>" \
  -m "<provider/model>" \
  -k 3 \
  -n 2 \
  -o ./jobs \
  --job-name pilot-vi
```

`build/pilot-vi` là sản phẩm do bước materialize tạo ra, chưa có sẵn. Lệnh trên chỉ minh họa một điều kiện; kế hoạch chạy phải bao phủ cả bốn biến thể A và hai biến thể B.

- [ ] Lưu cấu hình hiệu lực, phiên bản và danh sách trial trước khi chạy.
- [ ] Trộn thứ tự điều kiện; dùng môi trường sạch, không truyền lịch sử giữa trial.
- [ ] Chạy 3 lần cho từng điều kiện và từng cấu hình.
- [ ] Theo dõi lỗi hạ tầng; retry theo giao thức, không retry vì đáp án sai.
- [ ] Giữ artifact, trajectory và lý do retry; loại bỏ secrets trước chia sẻ.

Tổng pilot: `6 × 4 × 3 × 2 + 6 × 2 × 3 × 2 = 216 trial`, chưa tính smoke test, oracle và retry.

**Nghiệm thu:** có kết quả hoặc trạng thái lỗi rõ cho mọi trial dự kiến; số trial, mẫu số và chi phí có thể đối chiếu.

## 11. S9 — Review pilot và quyết định mở rộng

- [ ] Báo cáo điểm theo ngôn ngữ A; chênh lệch EN–VI theo điểm phần trăm.
- [ ] Báo cáo điểm B theo năng lực và ngôn ngữ instruction.
- [ ] Phân tích các ca fail đại diện và mọi ca nghi verifier chấm sai.
- [ ] Ước lượng độ bất định theo task/họ task, ghi rõ giới hạn cỡ mẫu nhỏ.
- [ ] Đo chi phí, thời gian trung bình và các trial đắt nhất.
- [ ] Nếu sửa task/verifier, tăng phiên bản; chấm/chạy lại các điều kiện bị ảnh hưởng một cách nhất quán.
- [ ] Viết `reports/pilot-report.md` và cập nhật backlog mở rộng.

Chỉ mở rộng khi không còn lỗi nghiêm trọng ở pipeline/verifier, các task đã có review và đã biết chi phí thực tế. Nếu chưa đạt, sửa đúng điểm yếu và kiểm định lại phần bị ảnh hưởng.

## 12. Lịch thực hiện đề xuất

| Khoảng thời gian | Công việc | Sản phẩm |
|---|---|---|
| Ngày làm việc 1–2 | S1: đặc tả, giao thức và yêu cầu baseline | Spec, protocol, quyết định ban đầu |
| Ngày 3 | S2: môi trường | Container và tài liệu môi trường |
| Ngày 4 | S3: chuẩn task | Template, manifest, checklist |
| Ngày 5–7 | S4: task hóa đơn | Task đã kiểm định |
| Ngày 8–9 | S5: task Unicode | Task đã kiểm định |
| Ngày 10 | S6: pipeline | Báo cáo kiểm định ban đầu |
| 1–2 tuần tiếp theo | S7–S9: đủ task, chạy và review pilot | Pilot 12 task và báo cáo |

Lịch tính theo ngày làm việc, điều chỉnh theo hạ tầng, reviewer và độ phức tạp thực tế. Không bỏ bước kiểm định để giữ lịch.

## 13. Checklist bàn giao giai đoạn đầu

- [ ] Có đặc tả A/B và giao thức chạy/chấm được version control.
- [x] Có môi trường được cố định và tài liệu tái lập.
- [x] Có 2 task đầu chạy xuyên suốt, oracle pass và negative controls fail.
- [x] Verifier dữ liệu chạy riêng, artifact được kiểm tra và reward không do agent quyết định; chưa audit mọi kiểu tấn công.
- [x] Có template, manifest và công cụ tổng hợp kết quả.
- [x] Có báo cáo kiểm định, vấn đề còn mở và backlog pilot.
- [ ] Trước mở rộng: pilot đã review, chi phí đã đo, điều kiện so EN–VI đã được xác nhận.
