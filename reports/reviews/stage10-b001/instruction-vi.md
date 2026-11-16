# Chuẩn hóa hóa đơn Việt Nam

Chuyển `/app/data/hoa_don.csv` thành hai file `/app/output/hoa_don.jsonl` và `/app/output/errors.jsonl`. Không thay đổi file nguồn.

CSV UTF-8 không BOM, phân cách dấu phẩy, quote theo CSV thông thường. Header là `invoice_id,customer_name,invoice_date,amount_vnd`. Mỗi record nằm trên một dòng vật lý; không có dòng rỗng. Có đúng bốn trường mỗi dòng; ID là chuỗi ASCII duy nhất không rỗng; tên không rỗng sau trim. Chỉ ngày và số tiền có thể không hợp lệ.

## Dòng hợp lệ

Mỗi dòng tạo một object với đúng bốn trường:

- `invoice_id`: chuỗi giữ nguyên.
- `customer_name`: chuỗi bỏ khoảng trắng hai đầu theo Unicode whitespace, chuẩn hóa NFC, giữ dấu và khoảng trắng bên trong.
- `invoice_date`: đầu vào đúng `dd/mm/yyyy` (2/2/4 chữ số ASCII), ngày lịch Gregory hợp lệ trong năm 0001–9999; đầu ra `yyyy-mm-dd`.
- `amount_vnd`: số nguyên JSON không âm. Đầu vào chấp nhận `0`, số nguyên không có số 0 thừa ở đầu (ví dụ `2500`), hoặc phân nhóm bằng dấu chấm: nhóm đầu 1–3 chữ số bắt đầu 1–9, sau đó một hay nhiều nhóm đúng 3 chữ số. Ví dụ `1.234.567` hợp lệ; `01`, `12.34`, `1234.567`, số âm, khoảng trắng, phần thập phân và ký hiệu tiền đều không hợp lệ. Không làm tròn.

Sắp xếp object hợp lệ theo `invoice_id` tăng dần dạng chuỗi ASCII.

## Dòng lỗi

Không đưa dòng lỗi vào file hóa đơn. Mỗi dòng lỗi tạo object với đúng hai trường `row_number` (số nguyên: dòng dữ liệu đầu là 2, header là 1) và `reason` (chuỗi `invalid_date` hoặc `invalid_amount`). Nếu cả hai sai, dùng `invalid_date`. Ghi theo thứ tự dòng nguồn tăng dần.

## Định dạng đầu ra

Cả hai file phải là UTF-8 không BOM, mỗi dòng đúng một object JSON, không dòng trống; mỗi file không quá 1 MiB. Chấp nhận LF/CRLF và có hoặc không newline cuối. Không chấp nhận duplicate key hoặc số NaN/Infinity. Thứ tự key và khoảng trắng JSON không ảnh hưởng điểm. Chỉ cần tạo artifact cho dữ liệu đã cung cấp, không bắt buộc nộp chương trình.
