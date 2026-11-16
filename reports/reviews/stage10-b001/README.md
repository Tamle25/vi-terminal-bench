# Gói review B001 — pending

Người dùng xác nhận ngày 13/11/2026: chưa có reviewer, chuẩn bị hồ sơ chờ review. Không có acceptance hoặc thời gian giải được tạo thay người review.

Gói mở đầu gồm instruction EN/VI, CSV đầu vào và pending record gắn task version/payload/prompt hash. Không chứa oracle, expected hoặc grader. CSV do generator công khai của task tạo; file nguồn phải giữ nguyên bytes. Người giải có thể bắt đầu trên workspace riêng; phần kiểm container/isolation cần môi trường đạt sau đó.

1. Đọc hai instruction và ghi giờ bắt đầu trước khi mở lời giải/expected trong repo.
2. Giải từ CSV, ghi command/artifact và thời gian thực. Đối chiếu từng ràng buộc EN/VI, ngày Gregory, ưu tiên lỗi, NFC và tiền VND.
3. Sau khi giải độc lập, dùng [hướng dẫn review](../../../docs/review-guide.md) để kiểm grader/controls/isolation và ghi điểm mơ hồ hoặc lỗi.
4. Hoàn thiện một review record với `reviewer_kind=human`, reviewer khác tác giả, ngày/thời gian thực và quyết định. File `pending-record.json` chỉ là template; không đổi accepted khi chưa thực hiện.
5. Nếu cần sửa task, ghi changes requested trước; payload/prompt thay đổi cần version/hash và kiểm/review tương ứng.

Để bắt đầu cần kỹ sư Việt Nam khác tác giả. AI tự kiểm không thay reviewer này. Dữ liệu và hồ sơ trong gói không chứng minh runtime đã sẵn sàng hoặc model đã được đánh giá.
