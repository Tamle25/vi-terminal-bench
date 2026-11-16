# Hướng dẫn review độc lập trước pilot

Reviewer là kỹ sư Việt Nam khác tác giả; chưa chỉ định người nào. Các hồ sơ trong reports/reviews là hồ sơ chờ review, không phải kết quả chấp nhận.

1. Chọn snapshot hash và đọc instruction EN/VI trước oracle/đáp án. Ghi thời điểm và thời gian giải thực tế.
2. Giải độc lập trên container sạch, ghi các điểm mơ hồ hoặc điều kiện không có trong instruction.
3. So kết quả với expected tĩnh; kiểm tra các case thường, biên và lỗi. Đối chiếu phép biến đổi bằng nguồn chuẩn khi cần.
4. Đọc grader và controls: tìm false positive/negative; thử cách giải hợp lệ khác, không chỉ oracle.
5. Kiểm tra fixture/expected không lộ trong agent image, kiểm tra artifact transfer trên Linux và cách ly verifier.
6. Review EN/VI theo từng ràng buộc, giữ path/identifier. Độ khó chỉ hiệu chỉnh sau thời gian giải và thí nghiệm model.
7. Ghi reviewer, ngày, hash, thời gian thực đo, nhận xét, lỗi và quyết định `accepted` hoặc `changes_requested`. Không cập nhật manifest thành reviewed trước bước này.

## Trọng tâm từng task

| Task | Các điểm cần đối chiếu |
|---|---|
| B001 | Ngày 03/04, leap year, nhóm tiền, bool khác int, ưu tiên invalid_date |
| B002 | NFC/NFD, case-distinct, thứ tự code point, collision, byte nhị phân |
| B003 | CP1258: đ/Đ và combining marks; byte 0x81 không định nghĩa; giữ newline/nguồn |
| B004 | đ mapping, NFD, casefold, substring, khoảng trắng/punctuation, giữ tên hiển thị |
| B005 | ICU 76.1/CLDR46, variant/lower/numeric off, NFC khi so và tie ID; giữ NFD hiển thị |
| B006 | BOM, delimiter, CRLF trong/ngoài ô, quote, ngày/tiền và ID số 0 đầu |

Nếu thay đổi hợp đồng/fixture/expected/grader sau kiểm định: tăng task version, ghi changelog, materialize và lập run manifest mới rồi kiểm định phần bị ảnh hưởng. Không sửa snapshot đã chạy mà vẫn giữ tên job cũ.
