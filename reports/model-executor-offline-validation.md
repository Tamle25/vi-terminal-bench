# Kiểm định đường executor offline — giai đoạn 5

Ngày 12/11/2026: bộ test Linux đạt **102/102**, không skip/failure/error. Kiểm định CLI riêng hoàn tất **2 trial fixture, 3 attempt, 5 request** qua ba tiến trình. **0 model/API call thật**, không có secret loader hoặc provider binding thực.

## Phạm vi được kiểm

| Kiểm tra | Bằng chứng/kết quả |
|---|---|
| Scope | Smoke chọn 1–2 trial rõ ràng; native pilot phải đủ 72 trial, hai cấu hình |
| Review | Scope smoke kiểm task con; pilot cần 6/6; fixture signoff và mẫu review trống không nhập được như review người thật |
| Gate sau preview | Config/prompt contract, snapshot, runtime expiry, review hash hoặc budget sai đều chặn trước request |
| Cấu hình hiệu lực | Settings được adapter fixture đọc riêng; thay settings/capability bị phát hiện |
| Accounting trong trial | Hai request có intent, reservation, claim và receipt riêng; vượt bound sau request đầu chặn request sau |
| Uncertain | Unknown cost giữ reservation; reward cuối đã biết vẫn xuất normalized; external uncertainty không bị ledger cục bộ xóa |
| Gián đoạn | Crash sau reserve/submit/receipt, crash qua child process thật và recovery bằng receipt không gửi lại |
| Tranh quyền | Hai controller không đồng thời dispatch hai trial; CAS giữ một chủ sở hữu attempt/request |
| Retry | Chỉ infra/verifier, tối đa ba attempt; agent failure không retry; phí các attempt lỗi vẫn giữ |
| Phân tách kết quả | Simulation cần plan riêng; model smoke bị từ chối khỏi pilot aggregate |
| CLI model | Chỉ validate, exit 2, không tạo execution state; manifest tự sinh được ghi là preview chưa thực thi |

Trong rà soát đã sửa việc gate ghi đè cờ `cost_uncertain` từ context bằng trạng thái local ledger. Gate hiện giữ cả hai nguồn uncertainty; có test thay đổi cờ sau request đầu và xác nhận request thứ hai bị chặn.

## Integration CLI và chi phí giả lập

Fixture có hai trial mục tiêu scope smoke, mỗi attempt thành công gồm hai request. Một attempt đầu gặp lỗi infra có phí 250 inference/50 compute micro-unit; retry thành công có hai request, trial còn lại có hai request.

1. Tiến trình thứ nhất chủ động dừng sau một attempt: một request lỗi đã lưu, cả hai trial chưa có kết quả cuối.
2. Tiến trình thứ hai resume: tổng ba attempt, năm request, hai kết quả cuối.
3. Tiến trình thứ ba chạy lại state đã hoàn tất: không tăng lượt fake dispatch.

Tổng phí request và attempt đều **4.250 inference + 450 compute micro-unit SIM_USD**. Không phải USD thực; `real_cost_usd=null`. Ba normalized attempt đối chiếu được với raw, request ledger và aggregate có nhãn simulation. Không công bố reward giả thành điểm năng lực model.

Archive sau khi các process đã đóng DB được giải nén và mở lại: hai kết quả cuối, năm lượt gọi, năm request ledger đều khớp. SHA-256: `e9445dbf2cd16da2c3aa85b8a1ce1de5457623b79b78274f0baa9925079c0207`.

## Nền tảng và khả năng tái lập

Toàn bộ regression và integration cuối chạy bằng Python **3.12.16 trên Linux/WSL**. Nguồn, configs, tasks, prompts và manifest được copy vào filesystem Linux; checksum từng file được kiểm trước/sau, không dùng cache hash để bỏ qua thay đổi giữa preview và request. Report unit ghi 172 input file đã kiểm cùng hash.

Lần chạy regression trực tiếp trên `/mnt/d` được dừng do I/O chậm; không dùng lần chưa hoàn tất đó làm bằng chứng đạt. Các lần gọi WSL mới cũng có thể mất Python trong `/tmp`, nên bootstrap dựng lại khi cần. Không thay pin task/harness hoặc sửa Docker để khắc phục việc này. Những con số trên là kết quả các lần native Linux đã hoàn tất.

## Bằng chứng và giới hạn

- [Test Linux và hash input](stage5-unit-tests.json).
- [Integration summary](stage5-offline-summary.json), [normalized fixture attempts](stage5-fixture-trials.jsonl).
- [Archive inputs/source/state/raw/requests/events](../jobs/stage5-scoped-executor.tar.gz).
- [Hợp đồng executor](../docs/model-executor-contract.md), [hướng dẫn CLI](../docs/model-executor.md).

Fixture chỉ chứng minh đường orchestration, không chứng minh giá provider, auth, cancellation, API isolation hoặc lookup/idempotency thật. Hiện partial multi-request chưa đủ receipt giữ uncertain và không tự tiếp tục; cần recovery policy của adapter thực. Restore kiểm tính bền vững dữ liệu, không bảo đảm dispatch từ đường dẫn prompt fixture đã di chuyển.

Chưa có reviewer, hai cấu hình thật hoặc budget. Không chạy lại 72 trial simulation, không chạy smoke/model thật, không tự accepted task. Xem [readiness bàn giao](stage5-readiness.md).
