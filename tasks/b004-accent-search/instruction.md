# Tìm khách hàng theo truy vấn không dấu

Đọc `/app/data/customers.json` (mảng object `id`, `name`) và `/app/data/queries.json` (mảng object `id`, `text`). ID là chuỗi ASCII duy nhất trong mỗi mảng; chuỗi Unicode hợp lệ, không sửa nguồn.

Khóa tìm kiếm được tạo cho cả tên và truy vấn bằng đúng thứ tự:

1. NFD.
2. Loại mọi code point có Unicode canonical combining class khác 0 (tương đương `unicodedata.combining(c) != 0`).
3. Đổi `đ` thành `d`, `Đ` thành `D`, rồi Unicode casefold.

So khớp **chuỗi con** của khóa truy vấn trong khóa tên. Không trim, gộp khoảng trắng, xóa dấu câu hoặc tìm trên ID. Khóa rỗng không được khớp tất cả khách hàng.

Ghi `/app/output/results.json`: mảng theo đúng thứ tự truy vấn. Mỗi object có đúng `query_id` (ID truy vấn), `matches` (mảng object đúng `id`, `name`), `error`. Sắp matches theo ID ASCII tăng dần. Giữ nguyên tên hiển thị theo nguồn, kể cả dạng NFD. Khóa rỗng: matches=[], error=`empty_query`; còn lại error=null, kể cả không có kết quả. Truy vấn trùng nội dung nhưng ID khác vẫn có kết quả riêng.

Artifact là file thường <=1 MiB, UTF-8 không BOM, JSON chuẩn không duplicate key/NaN/Infinity. Key order/khoảng trắng JSON tùy ý. Chỉ tạo artifact cho dữ liệu đã cho; không bắt buộc chương trình dùng lại.
