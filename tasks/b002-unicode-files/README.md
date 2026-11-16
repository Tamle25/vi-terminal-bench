# b002-unicode-files — Task card

- Track B; family `vn-unicode-files`; version 0.1.0; primary skill `unicode-files`.
- Độ khó dự kiến easy, thời gian chuyên gia 20–40 phút, chưa hiệu chỉnh.
- Công việc: copy sáu file, chuẩn hóa tên NFC và tạo index; nguồn giữ nguyên.
- Có cặp tên NFC/NFD nhìn giống nhau nhưng nội dung khác, tên khác hoa/thường, khoảng trắng, đ/Đ và nội dung nhị phân.
- Sắp xếp theo code point gốc; prefix ordinal áp dụng mọi file. Không đo collation tiếng Việt ở task này.
- Expected fixture được ghi riêng trong tests; grader kiểm tra danh sách, byte nguồn/đích, tên và index.
- Mutants: bỏ NFD, bỏ file, ghi đè nội dung, bỏ dấu tên, sai whitespace, sai hash/kiểu dữ liệu, symlink, nguồn thay đổi, index thiếu/sai thứ tự.
- Oracle trong solution; alternative/negative controls do công cụ validation tạo trong môi trường thử riêng.
- Tự tạo dữ liệu, license phát hành chờ chủ dự án; reviewer độc lập chưa có. Development.
