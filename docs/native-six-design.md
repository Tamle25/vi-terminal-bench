# Thiết kế bốn task mới và nguồn đối chiếu

Tất cả là artifact-only, fixture tổng hợp cho development, không kiểm tra code submission. Grader chỉ parse dữ liệu và đọc bytes; không import/chạy chương trình agent. Expected tĩnh nằm ngoài agent image. Chưa review độc lập và chưa chọn license phát hành.

## B003 — Windows-1258

Fixture dùng byte hex được viết rõ, không encode ngược từ oracle khi chấm. Đối chiếu [bảng CP1258 của Microsoft lưu tại Unicode](https://www.unicode.org/Public/MAPPINGS/VENDORS/MICSFT/WINDOWS/CP1258.TXT) ngày 12/11/2026: D0→Đ, E3→ă, F2→combining dot below, CC→combining grave; byte 81 không được định nghĩa. `d0 e3 f2 6e 67` chuẩn hóa NFC thành “Đặng”. Nguồn thứ hai có đ/ơ, dấu en dash và chữ Việt; nguồn rỗng và nguồn invalid được kiểm tra riêng.

Expected văn bản UTF-8 được viết tĩnh, không decode trong grader. Alternative dùng TextIOWrapper newline universal; oracle dùng decode strict và thay newline tường minh. Cùng codec chuẩn không thay thế việc review mapping độc lập. TCVN3/VNI chưa đưa vào phạm vi.

## B004 — Accent search

Fixture có NFC/NFD, đ/Đ, truy vấn hoa, dấu cách lặp, dấu gạch nối, truy vấn rỗng, không có kết quả và nội dung truy vấn lặp với ID khác. Match sets được viết theo các chỉ số khách hàng cụ thể, không tính lại bằng search trong grader. Tên hiển thị phải giữ nguyên byte Unicode logic nguồn, kể cả NFD.

## B005 — Vietnamese collation

Runtime Node22.14.0 dùng ICU76.1, CLDR46.0 và Unicode16.0; runtime Python của các task vẫn 3.12.12/Unicode15.0.0. Cấu hình ICU này được ghim bằng digest Node image; không đổi runtime B001/B002. B005 hiện nhắm Linux amd64 vì thư viện runtime copy từ đường dẫn x86_64.

Node full ICU cung cấp Intl.Collator; đã kiểm tra resolved options `vi`, sort, variant, lowercase first, numeric=false, ignorePunctuation=false. Nguồn phương pháp: [Node internationalization](https://nodejs.org/api/intl.html), [ICU collation API](https://unicode-org.github.io/icu/userguide/collation/api.html), đối chiếu ngày 12/11/2026.

Golden order được đóng băng theo dãy ID: N06,N17,N07,N16,N13,N03,N11,N05,N09,N02,N15,N08,N14,N10,N04,N12,N01. Đã đối chiếu implementation sort và insertion-sort trên cùng runtime, cùng các cặp a/ă/â, d/đ, e/ê, o/ô/ơ, u/ư; case lower-first, số dạng chuỗi và tie NFC/NFD. Grader chỉ đọc dãy object tĩnh, không cần Node hoặc ICU. Hai implementation cùng ICU không phải kiểm chứng human độc lập; trạng thái review vẫn pending.

Image được bổ sung Node cùng libstdc++/libgcc từ stage khóa digest; không tải package trong trial. `/opt/collation-runtime.json` trong agent image ghi runtime thực tế.

## B006 — CSV export

Chọn artifact-only: agent có thể sửa exporter lỗi nhưng chỉ output được chấm. Không tuyên bố đã kiểm tra code sửa hoặc mở mọi cấu hình Excel. Source-hash chỉ khóa dữ liệu orders; exporter được phép sửa.

Expected cells viết riêng; grader kiểm tra đúng một BOM, CRLF, parse CSV với delimiter đã công bố và so giá trị ô. Alternative quote mọi ô, oracle quote tối thiểu; cả hai phải pass. Có ID số 0 đầu, tiền 0/phân nhóm, leap date, semicolon/comma/quote và note nhiều dòng.
