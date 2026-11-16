# Thiết kế tập test kín — bản chuẩn bị

Sáu task hiện tại tiếp tục là development. Không đổi tên, đổi con số hoặc dịch instruction để gọi cùng họ task là private test mới. Chưa tạo hoặc phát hành bộ test kín trong giai đoạn này.

## Ma trận family đề xuất

| Nhóm | Family development đã có | Family test mới cần viết từ tình huống khác |
|---|---|---|
| Số/ngày/tiền | Chuẩn hóa hóa đơn | Đối soát sao kê có số âm/làm tròn và ngày chốt sổ rõ |
| File Unicode | Copy/index NFC/NFD | Khôi phục manifest backup và giải quyết collision, không dùng lại pipeline copy |
| Encoding | CP1258 có nhãn | Di chuyển kho văn bản nhiều nguồn có metadata và báo lỗi; TCVN3/VNI chỉ sau xác minh mapping/license |
| Search | Substring không dấu | Ghép danh mục/tên địa điểm theo quy tắc đối chiếu khác, tránh tái dùng match sets |
| Collation | Sắp danh mục ICU | Pagination/grouping theo collation, tie-break và bản ghi đồng hạng rõ |
| CSV | Artifact xuất CSV | Sửa pipeline nhập/xuất có nhiều file hoặc log, hợp đồng và giao diện kiểm chứng riêng |

Đây là backlog ý tưởng, chưa có task được kiểm định hoặc giấy phép phát hành. Tình huống có yêu cầu kỹ thuật chung vẫn cần review mức trùng lặp; không mặc định đổi bối cảnh là đủ độc lập.

## Quy trình

1. Gắn family_id trước chia split; kiểm trùng task logic, fixture, oracle và cấu trúc lỗi với development.
2. Tạo dữ liệu tổng hợp/được cấp quyền, không dùng thông tin cá nhân thật. Ghi nguồn, version và reviewer.
3. Giữ test/expected/oracle tách agent image; công bố mọi điều kiện chấm trong instruction/spec. Test kín không được chứa yêu cầu ẩn.
4. Chọn nơi lưu và quyền truy cập cùng chủ dự án trước khi đưa dữ liệu kín vào dịch vụ ngoài; không tự upload từ kế hoạch này.
5. Khóa snapshot trước đánh giá; mọi sửa chấm cần version/changelog và đánh giá lại đối xứng.

## Thống kê và phạm vi suy luận

Native-six có một family mỗi skill nên CI stratified-family B hiện null. Hai family/skill chỉ là mức tối thiểu của công cụ, không bảo đảm CI đủ chính xác. Phải chọn quy mô theo độ bất định thực nghiệm; không tăng số repeat để giả thay số family độc lập.

Có thể chạy pilot chẩn đoán 72 trial sau khi đủ review/profile/runtime mà không cần viết xong bộ kín. Báo cáo hạn chế cỡ mẫu và contamination. Artifact-only không chứng minh agent đã viết chương trình tổng quát; nếu cần đo chương trình tổng quát, tạo task có giao diện công khai, hidden inputs trong phạm vi hợp đồng và worker thực thi submission được cách ly riêng.
