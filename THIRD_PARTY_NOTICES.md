# Nguồn và quyền sử dụng

Hiện tại sáu task B và fixture là nội dung tổng hợp mới trong dự án, không sao chép task mẫu. Tên người/tổ chức trong fixture là dữ liệu giả để kiểm thử. Chủ dự án chưa chọn giấy phép phát hành nội dung mới; chưa công bố quyền tái sử dụng như một bản phát hành open source.

| Nguồn | Cách sử dụng hiện tại | Trạng thái |
|---|---|---|
| [Terminal-Bench](https://github.com/harbor-framework/terminal-bench) | Tham khảo cấu trúc/phương pháp, chưa nhập task | Repo ghi Apache-2.0; cần xác minh snapshot và thành phần trước kế thừa |
| [Terminal-Bench-LILT](https://github.com/lilt/terminal-bench-lilt) | Chỉ tham khảo phương pháp task bản địa | Chưa xác minh license task mẫu; không tái phân phối |
| [Harbor](https://github.com/harbor-framework/harbor) | Dependency harness | Package mục tiêu 0.25.0, Apache-2.0; lưu lock khi cài |
| [Node runtime](https://github.com/nodejs/node/blob/v22.14.0/LICENSE) | B005: Node22.14.0, ICU76.1/CLDR46.0; binary và thư viện hệ thống từ stage khóa digest | Giữ điều khoản Node/ICU và dependency; không cấp lại license thay upstream |
| [Python image](https://hub.docker.com/_/python) | Runtime container | Lưu tag/digest và điều khoản upstream; không coi license dự án bao phủ dependency |

Ngày đối chiếu: 12/11/2026. Khi nhập dữ liệu bên ngoài phải bổ sung URL, ref/hash, attribution, license và NOTICE liên quan.
