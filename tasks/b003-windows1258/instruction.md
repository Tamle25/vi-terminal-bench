# Chuyển dữ liệu Windows-1258 sang UTF-8

`/app/data/sources.json` là mảng có thứ tự, mỗi object có `file` (tên file .bin trực tiếp trong `/app/data`) và `encoding` (luôn `windows-1258`). Tên file ASCII duy nhất; metadata hợp lệ. Nguồn có thể rỗng hoặc chứa byte không hợp lệ. Không đổi byte của bất kỳ file nguồn/metadata nào.

Với từng nguồn theo thứ tự metadata:

1. Giải mã Windows-1258 **strict**. Nếu có byte không được định nghĩa, không tạo file văn bản cho nguồn đó; không dùng replacement hoặc ignore.
2. Nguồn hợp lệ: đổi CRLF và CR đơn thành LF, chuẩn hóa toàn văn bản NFC, giữ mọi nội dung khác. Không tự thêm newline. Ghi UTF-8 không BOM vào `/app/output/text/<stem>.txt`, với stem là tên nguồn bỏ `.bin`. Nguồn rỗng tạo file rỗng.
3. Tạo `/app/output/report.json`, là mảng có cùng thứ tự nguồn, mỗi object có đúng `file`, `status`, `output`. Nguồn hợp lệ: status=`converted`, output là tên file .txt không kèm thư mục. Nguồn lỗi: status=`invalid_encoding`, output=null.

Thư mục `text` chỉ chứa các file chuyển đổi thành công, không có file thừa/thư mục con/symlink. Artifact là file thường <=1 MiB; JSON UTF-8 không BOM, không duplicate key hoặc NaN/Infinity, thứ tự key/khoảng trắng tùy ý. Chỉ cần tạo artifact cho dữ liệu đã cho, không bắt nộp chương trình. Windows-1258 có thể biểu diễn dấu thanh bằng combining marks; NFC không đồng nghĩa bỏ dấu.
