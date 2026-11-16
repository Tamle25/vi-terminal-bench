# Sắp xếp danh mục theo collation tiếng Việt

Đọc `/app/data/catalog.json`, mảng object có đúng `id` (ASCII duy nhất) và `name` (Unicode). Không đổi nguồn. Ghi `/app/output/catalog.json`, chứa toàn bộ object gốc theo thứ tự mới; không sửa tên hiển thị hoặc thêm/bớt trường.

So tên sau chuẩn hóa NFC bằng collation tiếng Việt của **ICU 76.1, CLDR 46.0**, tương đương Node 22.14.0:

```javascript
new Intl.Collator('vi', {
  usage: 'sort', sensitivity: 'variant', caseFirst: 'lower',
  numeric: false, ignorePunctuation: false
})
```

Locale `vi`, collation `default`; sensitivity variant tương ứng phân biệt dấu và hoa/thường (tertiary), lowercase trước uppercase khi khác case. Numeric collation tắt: không tự coi dãy số như số nguyên. Nếu collator cho hai tên bằng nhau, tie-break theo ID ASCII tăng dần. Chuẩn hóa chỉ dùng khi so sánh; tên đầu ra giữ nguyên Unicode nguồn.

Runtime `node` đã có sẵn trong image, full ICU; `/opt/collation-runtime.json` ghi phiên bản và resolved options. Có thể dùng công cụ khác nếu kết quả tương đương; không tải package qua mạng.

Đầu ra là mảng JSON UTF-8 không BOM, file thường <=1 MiB; không duplicate key/NaN/Infinity. Key order/khoảng trắng tùy ý. Chỉ cần artifact cho dữ liệu đã cho, không bắt nộp chương trình. Thứ tự code point hay bỏ dấu rồi sort không thay thế collation này.
