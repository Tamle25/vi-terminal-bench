# Backlog sau mốc kỹ thuật M1

Cập nhật 12/11/2026: các task B003–B006 và công cụ adapter/coverage/bootstrap bên dưới đã được triển khai, kiểm định trong [native-six-validation.md](native-six-validation.md). Danh sách cũ được giữ làm lịch sử; phần còn mở hiện tại theo [pilot-readiness.md](pilot-readiness.md): review độc lập, latency verifier, cấu hình model/ngân sách, nguồn A và split/license.

## Có thể tiếp tục trước khi có baseline A

- Review độc lập hai instruction, expected output, negative controls và phân loại độ khó.
- B003: chuyển Windows-1258 sang UTF-8 có nhãn nguồn; bổ sung TCVN3/VNI sau khi xác minh bảng ánh xạ, dữ liệu và quyền dùng.
- B004: tìm kiếm không dấu với quy tắc đ/Đ, casefold và phạm vi khớp công bố rõ.
- B005: collation tiếng Việt, pin ICU/CLDR và tie-break; không dùng thứ tự code point của B002 làm đáp án collation.
- B006: sửa quy trình xuất CSV/log tiếng Việt, chốt BOM, delimiter, quote và newline theo môi trường mục tiêu.
- Đo thời gian/chi phí thực tế và thiết kế split theo family_id.
- Viết adapter model/Harbor sang trial schema, kiểm định phân loại lỗi và retry; thêm CI theo họ task trước báo cáo chính thức.

## Chờ đầu vào người phụ trách/Eval

- Snapshot, cấu hình baseline và quyền dùng task A theo docs/eval-input-checklist.md.
- Chọn hai cấu hình agent/model cùng ngân sách và phương thức API phù hợp sandbox offline.
- Reviewer độc lập và quyết định giấy phép phát hành.

## Điều kiện chạy pilot

Đủ 12 task gốc đã được kiểm định/review, bốn instruction mỗi task A và hai mỗi task B, cấu hình và chi phí dự kiến rõ, môi trường Linux giữ được tên file, lưu đủ provenance và 3 repeat độc lập. Chưa đạt các điều kiện này thì giữ trạng thái development.
