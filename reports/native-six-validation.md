# Kiểm định kỹ thuật native-six — Giai đoạn 2

Ngày báo cáo: 12/11/2026, giờ Việt Nam. Trạng thái: sáu task B development đã chạy xuyên suốt; chưa đánh giá model hoặc hoàn thành review độc lập.

## Phạm vi đã triển khai

| Task | Năng lực chính | Oracle Harbor | No-op Harbor |
|---|---|---|---|
| b001-vn-invoice | Số tiền/ngày/Unicode | 3/3 reward 1 | 1/1 reward 0 |
| b002-unicode-files | File NFC/NFD và case-distinct | 3/3 reward 1 | 1/1 reward 0 |
| b003-windows1258 | Windows-1258 → UTF-8/NFC | 3/3 reward 1 | 1/1 reward 0 |
| b004-accent-search | Tìm không dấu, đ/Đ, NFD | 3/3 reward 1 | 1/1 reward 0 |
| b005-vietnamese-collation | ICU Vietnamese collation | 3/3 reward 1 | 1/1 reward 0 |
| b006-vietnamese-csv-export | CSV BOM/CRLF/quote/ngày/tiền | 3/3 reward 1 | 1/1 reward 0 |

Tổng **18 oracle + 6 nop**, không exception trong kết quả trial; tất cả dùng verifier riêng. Đây là kiểm định pipeline và đáp án tham chiếu, không phải tỷ lệ thành công của model. Chỉ instruction VI được chạy qua Harbor; EN được materialize, kiểm hash payload và vẫn chờ review ngôn ngữ. Không nhân đôi oracle để suy ra năng lực hiểu EN/VI.

## Bằng chứng

- [native-six-summary.json](native-six-summary.json): kết quả 24 trial, số controls, checksum archive và kết quả khôi phục.
- [native-six-controls.json](native-six-controls.json): **125/125 control đúng kỳ vọng**, gồm 24 positive và 101 negative. Giữ nguyên 45 ca M1.
- [native-six-unit-tests.json](native-six-unit-tests.json): **27/27 test trên Linux**, không skip; gồm coverage, retry, checksum, adapter, bootstrap cặp và filesystem/wrapper.
- [native-six-agent-images.json](native-six-agent-images.json): cả sáu image agent không chứa /tests, /solution hoặc expected trong /app. Không phải audit bảo mật toàn diện.
- [native-six-oracle-run.json](native-six-oracle-run.json), [native-six-nop-run.json](native-six-nop-run.json): manifest lập trước khi chạy, định danh repeat và mapping job rõ ràng.
- [native-six-oracle-trials.jsonl](native-six-oracle-trials.jsonl), [native-six-nop-trials.jsonl](native-six-nop-trials.jsonl): mọi attempt chuẩn hóa kèm raw reference.
- [native-six-oracle-results.json](native-six-oracle-results.json), [native-six-nop-results.json](native-six-nop-results.json): coverage đủ theo scope VI đã lập, điểm development tương ứng 1 và 0. Không trộn vào bảng điểm model.
- [m1-archive-audit.json](m1-archive-audit.json): archive M1 được giải nén trên Linux, cả 8 trial khớp báo cáo cũ.
- [m1-legacy-adapter-audit.json](m1-legacy-adapter-audit.json): adapter khớp sáu raw oracle M1 bằng binding hậu kiểm tường minh; không giả nhận M1 đã có run manifest trước khi chạy.

## Thay đổi công cụ

Registry development tường minh cho từng task, không có fallback B002. Image check theo manifest và trả lỗi khi không đạt. Kiểm tra container sống dùng exact Compose project label. Preflight thử case/NFC/NFD trên filesystem và kiểm Docker Linux, Compose offline. Dataset validation kiểm schema, COPY sources, source-hashes, prompt, version và artifact.

Planner/runner chỉ thực thi oracle/nop; mỗi repeat thành một job `-k 1 -r 0`, nên trial ID và repeat được biết trước. Adapter từ chối checksum/config lệch, retry hoặc raw trial không được khai báo, unknown exception và reward không hợp lệ. Job thiếu output của nop có log engine-cp không tìm thấy output; grader hoàn tất và cho reward 0 đúng bài toán. Không coi riêng dòng cảnh báo đó là lỗi truyền dữ liệu của một artifact vốn tồn tại.

Bootstrap dùng family clusters, B phân tầng theo nhóm năng lực, EN–VI dùng cùng cặp. Với một family/skill hiện tại, CI B là null với lý do thiếu replication; không xuất CI giả hoặc kết luận thứ hạng. Cấu hình hoàn toàn không có trial vẫn bị phát hiện từ run manifest.

## Runtime và bảo toàn snapshot

Kiểm tra cuối phát hiện thứ tự so sánh Path phụ thuộc Windows/Linux trong công cụ hash payload. Đã sửa thành sắp chuỗi relative POSIX theo code point và thêm regression test trên hai hệ điều hành. Hash canonical mới khớp tất cả hash đã lập trước trong run manifest Linux; không thay đổi task hoặc kết quả verifier. Snapshot M1 cũ được giữ làm lịch sử với thứ tự Path cũ; native-six snapshot và hồ sơ review dùng thuật toán canonical. Audit M1 mới đối chiếu cả checksum Harbor nguồn trước khi gán canonical payload hash.

- Python task 3.12.12, Unicode15.0; harness Python3.12.16/Harbor0.25.0 giữ khóa từ M1.
- B005 thêm Node22.14.0/ICU76.1/CLDR46.0/Unicode16.0, từ Node image khóa digest. Chỉ B005 có runtime bổ sung; hiện Linux amd64.
- [Thiết kế task và nguồn đối chiếu](../docs/native-six-design.md), [manifest](../manifest.jsonl).
- Dataset EN/VI tại `build/native-six-portable-en` và `build/native-six-portable-vi`; [native-six-task-snapshot.json](native-six-task-snapshot.json) ghi hash. Payload ngoài instruction giống nhau giữa hai ngôn ngữ.
- Archive `jobs/native-six-validation.tar.gz` đã được khôi phục thử; jobs bị Git ignore. Raw Linux jobs nằm dưới `/tmp/vi-terminal-bench-runtime/jobs/native-six-*`.
- Không đổi nội dung B001/B002; nguồn và checksum task của chúng được giữ nguyên. Bốn task mới không dùng TCVN3/VNI hoặc dữ liệu riêng tư.

## Thời gian, chi phí và nhiễu

Theo raw trial timestamps, tổng thời gian trial (không phải elapsed wall time của cả đợt) là khoảng 2.754,68 giây cho oracle và 210,77 giây cho nop. Hai trial B005/B006 repeat 1 kéo dài khoảng 1.088/1.090 giây; riêng pha verifier khoảng 1.071/1.072 giây, trong khi agent thực thi khoảng 1,23/0,72 giây. Hai repeat tiếp theo của chúng khoảng 34–37 giây/trial.

Chưa xác định nguyên nhân gốc của nhiễu pha verifier/khởi tạo/transfer đó. Không diễn giải thời gian này thành độ khó task, tốc độ model hoặc chi phí inference. Trước pilot model cần kiểm tra warm build, transfer và tải Docker; chưa chứng minh hiệu năng ổn định cho vận hành dài hạn. Không gọi API model; chi phí compute/điện/lưu trữ chưa được quy đổi USD, giữ null.

Probe cuối phiên: Docker API từ Windows phản hồi, nhưng Docker CLI trong WSL timeout sau 30 giây. [native-six-preflight-final.json](native-six-preflight-final.json) ghi trạng thái fail-fast; các preflight trước khi chạy 24 trial đã thành công và được lưu riêng. Đã thêm timeout và kết quả ready=false khi probe lỗi, dừng probe chỉ đọc cũ bị kẹt; không restart Docker hay workload khác. Đây là vấn đề đường truy cập/runtime cần giải quyết trước pilot, không gán thành lỗi model hoặc thay đổi reward các trial đã hoàn tất.

## Điều kiện còn thiếu

Sáu [hồ sơ review](../docs/review-guide.md) được tạo với trạng thái pending, chưa có reviewer, ngày review hoặc thời gian giải thực đo. Chưa có task A/baseline Eval, cấu hình model/ngân sách, giấy phép phát hành hay test split kín. Xem [pilot-readiness.md](pilot-readiness.md). Hoàn tất native-six kỹ thuật không đồng nghĩa hoàn tất toàn bộ giai đoạn 2 hoặc pilot.
