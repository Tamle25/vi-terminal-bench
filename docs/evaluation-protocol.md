# Giao thức đánh giá v0.1

## Cố định điều kiện

Lưu dataset/task/instruction/verifier hash, image digest, Harbor/version, Python/Unicode, agent/version, model định danh cụ thể, system prompt, công cụ, mạng, timeout, CPU/RAM, token/turn/effort nếu áp dụng, thứ tự và thời điểm chạy.

Harbor mục tiêu 0.25.0, task schema 1.4. Môi trường task B: Python 3.12 Linux, `C.UTF-8`, timezone `Asia/Ho_Chi_Minh`, 1 CPU, 1 GiB RAM. Agent timeout 300 giây, verifier 60 giây cho development. Đây không phải cấu hình cho task A kế thừa. Mạng agent và verifier bị tắt tĩnh bằng `network_mode: none` trong cả hai file Docker Compose. Task TOML để policy Harbor là `public` vì kernel WSL hiện tại không đáp ứng backend egress động của Harbor; Compose mới là cơ chế thực thi không mạng. Cấu hình này dành cho Docker/Compose, không suy ra đảm bảo trên provider bỏ qua Compose. Trước model run cần chọn agent chạy ngoài sandbox hoặc chuẩn bị sẵn agent và chính sách API tương thích.

## Trial và lỗi

Ba lần độc lập mỗi task/condition/configuration; môi trường sạch, không truyền lịch sử. Trộn thứ tự khi chạy model. Retry tối đa 2 lần bổ sung chỉ cho lỗi hạ tầng được xác định; giữ mọi attempt và lý do. Không retry lời giải sai. Chưa có cấu hình/model/ngân sách nên chưa chạy model trial.

| Trạng thái chuẩn hóa | Ý nghĩa | Reward |
|---|---|---|
| completed | Verifier hoàn tất kiểm tra | 0 hoặc 1 |
| agent_timeout | Agent vượt ngân sách đã công bố | 0 |
| agent_error | Agent/model không hoàn thành, không thuộc lỗi hạ tầng | 0 |
| infra_error | Lỗi provider, container, transfer, harness | null |
| verifier_error | Lỗi thực thi nội bộ grader/test | null |

Thiếu/sai artifact do agent là fail task. Transfer thất bại do hệ thống là infra_error. Verifier exit 0=pass, 1=artifact không đạt, 2=lỗi nội bộ; test.sh không chuyển exit 2 thành reward 0 hợp lệ. Lưu log để phân biệt timeout do agent với timeout của hạ tầng. Nếu còn trial lỗi sau retry, điểm đó chỉ là provisional; không tuyên bố đủ số lượt đánh giá.

## Định dạng trial chuẩn hóa

`scripts/aggregate_results.py` nhận JSONL chuẩn hóa; `scripts/import_harbor_results.py` chuyển output Harbor 0.25.0 theo run manifest, không đoán repeat từ tên thư mục. Một hàng cho một attempt, UTF-8:

```json
{"trial_id":"b001-vi-cfg-r1","attempt":1,"task_id":"b001-vn-invoice","family_id":"vn-invoice","track":"B","skill":"number-date","language":"vi","configuration":"oracle-development","repeat":1,"status":"completed","reward":1,"duration_sec":0.5,"cost_usd":null}
```

`trial_id` xác định một lượt dự kiến; retry giữ ID và tăng attempt liên tiếp. Chỉ retry sau infra_error/verifier_error. Mỗi cấu hình/task/ngôn ngữ phải có các repeat 1..3 để đủ giao thức. Các trial kiểm định (oracle, mutant, alternative) lưu ở báo cáo kiểm định riêng, không đưa vào bảng điểm model.

## Điểm

Trong mỗi cấu hình/ngôn ngữ: trung bình reward qua repeat của từng task, sau đó trung bình trên task; lỗi hạ tầng chưa giải quyết giữ riêng, công bố mẫu số. Điểm tổng B khi đủ các nhóm là trung bình đều điểm nhóm. Không trộn task A/B. Chênh lệch EN–VI = 100 × (VI−EN), đơn vị điểm phần trăm, chỉ tính trên tập task và điều kiện khớp.

Kết quả thiếu repeat/task hoặc còn lỗi hạ tầng không phải bảng điểm cuối. Không gọi “pass ít nhất một trong ba lần” là pass@1. Báo cáo phát hành cần CI bootstrap theo task/họ task và paired EN–VI; công cụ tổng hợp development chưa tính CI và không tạo thứ hạng.

### Cập nhật giai đoạn 2

Đã triển khai CI bootstrap 95% theo họ task, seed mặc định 20261112, 2.000 lượt. Track B resample family trong từng nhóm năng lực để giữ macro-average; nếu nhóm có ít hơn hai family, trả `ci95=null` với lý do không đủ replication. Family B đi qua nhiều skill-strata cũng được báo chưa hỗ trợ thay vì giả định độc lập. Native-six hiện có một family mỗi nhóm nên chưa ước lượng CI B theo phương pháp này. Delta EN–VI lấy mẫu cùng family và task cặp; các repeat/bản dịch không được coi là task mới.

Run manifest lập trước phải có planned trial ID, configuration, language, repeat, snapshot/checksum và mapping attempt→job. `aggregate_results.py --run-plan` phát hiện thiếu cả configuration không xuất hiện trong input, kiểm provenance và retry. Adapter từ chối raw trial không dự kiến, checksum/cấu hình lệch, reward thiếu/không hữu hạn và exception chưa được phân loại. Lỗi chưa biết cần bảng phân loại tường minh; giữ raw reference, không mặc định reward 0.

Planner/runner hiện chỉ thực thi oracle/nop development, không chạy model. Adapter đã kiểm định cho profile timeout mặc định và không override resource/agent history; model profile ngoài phạm vi này phải được cấu hình, mở rộng mapping và kiểm tra trước. Audit M1 dùng binding hậu kiểm ghi rõ nhãn, không tuyên bố M1 đã có pre-execution manifest.

## Nghiệm thu task và thay đổi phiên bản

Oracle pass 3/3 môi trường mới; no-op và mọi mutant đã định nghĩa phải fail; một cách giải khác hợp lệ phải pass. Review độc lập còn là điều kiện phát hành. Sửa task/verifier phải tăng version, ghi changelog và đánh giá lại mọi điều kiện bị ảnh hưởng; không thay đổi một phía EN–VI.
