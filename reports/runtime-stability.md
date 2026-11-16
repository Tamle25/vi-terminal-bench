# Đo ổn định có mục tiêu giai đoạn 3

Không chạy lại toàn bộ24 trial. Chọn B005/B006, đơn luồng, hai repeat, container sạch, giữ image cache sẵn có. Repeat1 là lần đầu của phiên với cache tồn tại, **không gọi là cold build**; repeat2 dùng lại image. Không prune cache hoặc workload khác.

| Task | Repeat | Tổng trial (s) | Setup (s) | Agent (s) | Pha verifier (s) |
|---|---:|---:|---:|---:|---:|
| B005 | 1 | 37,55 | 5,41 | 0,86 | 20,07 |
| B006 | 1 | 42,58 | 12,90 | 1,00 | 14,87 |
| B005 | 2 | 31,21 | 2,74 | 0,72 | 16,19 |
| B006 | 2 | 30,69 | 2,82 | 0,62 | 16,13 |

Nguồn: [smoke summary](stage3-smoke-summary.json), [manifest trước chạy](stage3-smoke-run.json), [trial chuẩn hóa](stage3-smoke-trials.jsonl). Cả4 reward1, không exception, separate verifier. Hash task/nguồn giữ nguyên; archive `jobs/stage3-targeted-smoke.tar.gz` được khôi phục kiểm tra trên Linux.

Phạm vi chạy là relay tạm tới proxy Docker Desktop hoạt động; default WSL path chưa đạt preflight. Không có model/API call. Hai job deadline300 giây, relay command deadline660 giây; các giới hạn này cho hạ tầng development, không đổi budget task.

## Timeout và độ phân giải dữ liệu

Đã đọc source Harbor0.25.0: `trial/single_step.py` ghi TimingInfo verifier bao quanh `_run_separate_verifier`; trong `trial/trial.py`, tạo/start verifier environment và upload artifact diễn ra trước `_verify_with_timeout`. Hàm này mới áp `asyncio.wait_for(verifier.verify(), timeout_sec)`. Vì vậy task verifier timeout60 giây không phải giới hạn cho toàn bộ TimingInfo verifier gồm setup/transfer/teardown.

Outlier cũ khoảng1.071/1.072 giây thuộc pha verifier rộng; chưa có timestamps đủ chi tiết để gán riêng build, upload, grader hoặc teardown cho từng giây. Không khẳng định tăng timeout60 giây là cách sửa. Không sửa task để xử lý hiện tượng đó.

## Kết luận có giới hạn

Không tái diễn outlier trong4 smoke qua scoped endpoint; đường này đủ bằng chứng cho kiểm định cục bộ đã chạy. Không chứng minh nguyên nhân gốc của outlier cũ hoặc độ ổn định dài hạn, và chưa kiểm lại concurrency2. Các giả thuyết còn mở: integration socket, setup/transfer, cache và tải đồng thời. Không tính thời gian pha này thành tốc độ model hoặc lập trần tiền inference từ nó.

Trước pilot có phí cần chốt profile runtime/network cụ thể, kiểm tra lại readiness và concurrency đã chọn. Giữ lịch sử default path fail; không tuyên bố runtime mặc định đã được sửa.
