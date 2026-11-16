# Bảo toàn dữ liệu khi chuẩn hóa tên file tiếng Việt

Thư mục `/app/incoming` chứa các file thường, tên Unicode hợp lệ, không có thư mục con hoặc symlink. Có thể có tên khác nhau về hoa/thường, dấu cách và dạng Unicode NFC/NFD, kể cả hai tên nhìn giống nhau. Nội dung có thể là nhị phân. Không thay đổi tên hoặc byte của nguồn.

Hãy sao chép toàn bộ file sang `/app/output/files` và tạo `/app/output/index.jsonl` theo quy tắc:

1. Liệt kê tên gốc chính xác, rồi sắp xếp tăng dần theo dãy Unicode code point của tên gốc (tương đương Python `sorted` trên chuỗi). Không chuẩn hóa, bỏ dấu, casefold hoặc dùng locale collation khi sắp xếp.
2. Đánh số từ 1 theo thứ tự đó. Tên đích của mọi file là số thứ tự ít nhất 4 chữ số, thêm `--`, rồi tên gốc chuẩn hóa NFC. Ví dụ file thứ nhất có tên `Đơn.txt` sẽ thành `0001--Đơn.txt`. Tiền tố số khác nhau giải quyết va chạm sau NFC. Không bỏ dấu hoặc đổi hoa/thường.
3. Sao chép chính xác byte sang tên đích. Thư mục `files` phải chỉ chứa các file đích, không có file dư, thư mục con hoặc symlink.
4. Index ghi theo cùng thứ tự, mỗi dòng là một object có đúng các trường: `source` (tên gốc chính xác, không chuẩn hóa), `target` (tên file đích, không kèm thư mục), `sha256` (hex SHA-256 chữ thường của nội dung), `size_bytes` (số nguyên JSON là số byte).
5. Index dùng UTF-8 không BOM, không dòng trống, mỗi dòng một object JSON; kích thước không quá 1 MiB. Chấp nhận LF/CRLF và có hoặc không newline cuối. Không duplicate key hoặc số NaN/Infinity. Thứ tự key và khoảng trắng JSON không ảnh hưởng điểm.

Chỉ cần tạo artifact cho dữ liệu đã cung cấp, không bắt buộc nộp chương trình. Giữ nguyên dấu tiếng Việt và phân biệt các file nguồn có nội dung khác nhau.
