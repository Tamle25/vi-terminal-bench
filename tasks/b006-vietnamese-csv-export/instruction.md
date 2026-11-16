# Xuất CSV tiếng Việt đúng hợp đồng nhập

`/app/export.py` là exporter cũ đang sai định dạng. Đọc `/app/data/orders.json` và tạo `/app/output/orders.csv`. Bạn có thể sửa exporter hoặc tạo artifact bằng cách khác; verifier chỉ chấm CSV, không chạy code bạn viết và không kiểm tra file exporter đã sửa. Không đổi byte của `data/orders.json`.

Input là mảng object `id` (ASCII duy nhất), `customer`, `date` (ngày ISO hợp lệ), `amount_vnd` (số nguyên không âm), `note` (chuỗi Unicode có thể rỗng, chứa dấu câu/quote/xuống dòng).

Hợp đồng CSV:

- Đúng một UTF-8 BOM ở đầu, delimiter `;`, quote `"` theo CSV thông thường (quote bên trong ô được lặp đôi). Chấp nhận quote tối thiểu hoặc quote toàn bộ ô.
- Header chính xác theo thứ tự: `ma_don;khach_hang;ngay;so_tien_vnd;ghi_chu`.
- Record tăng dần theo ID ASCII; `ma_don` giữ nguyên ID kể cả số 0 đầu, khách hàng giữ nguyên dấu.
- Ngày thành `dd/mm/yyyy`; tiền phân nhóm nghìn bằng dấu chấm, không thập phân/ký hiệu tiền; số 0 thành `0`.
- Note giữ nguyên mọi nội dung ngoài việc chuẩn hóa CRLF/CR/LF về CRLF. Mọi xuống dòng trong toàn file (cả trong ô) phải là CRLF; record cuối cũng có CRLF. Không thêm dòng rỗng.
- Giá trị từng ô phải đúng; không thêm apostrophe, công thức, cột phụ hoặc dòng hướng dẫn `sep=`.

Artifact là file thường <=1 MiB. Đây là hợp đồng định dạng cụ thể, không yêu cầu mở ứng dụng Excel hay bảo đảm hành vi tự suy luận kiểu dữ liệu của mọi phiên bản Excel. Chỉ cần đầu ra cho dữ liệu đã cung cấp.
