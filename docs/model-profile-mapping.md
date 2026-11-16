# Mapping model profile và cấu hình hiệu lực

Trạng thái: hợp đồng dữ liệu và fixture đã kiểm định; **chưa có adapter agent thật được chọn hoặc kiểm định**. [Template](../configs/model-pilot.template.json) vẫn giữ các quyết định chưa có ở dạng null, không có credentials.

| Thành phần | Giá trị cần đối chiếu khi có agent thật |
|---|---|
| Agent/provider | Agent/version, model ID, provider, endpoint, effort |
| Prompt | Nội dung system prompt đã đọc và SHA-256, không chỉ đường dẫn |
| Hành vi | Kwargs theo allowlist của đúng adapter, tools, max tokens/turns/time |
| Môi trường | Kiến trúc API host/container, network policy thực thi, tài nguyên và concurrency |
| Runtime | Stable profile fingerprint; endpoint tạm đối chiếu trong attestation riêng |
| Budget | Caps smoke/inference/compute, reservation và nguồn giá hiện hành |
| Secret | Chỉ tên biến/cơ chế cấp secret; giá trị không vào repo, profile hash hoặc report |

`model_dry_run.py` kiểm tra schema, fingerprint cấu hình và preview trial. `pilot_contracts.configuration_contract()` mô tả hợp đồng expected/effective mở rộng; `compare_effective()` phát hiện khác biệt dữ liệu. Cả hai là helper thuần, không chứng minh agent đã dùng các giá trị đó.

Readiness hiện yêu cầu evidence `kind=agent-verified`, map chính xác configuration fingerprints của preview và runtime profile hash. Các fixture trong test chỉ chứng minh gate xử lý hợp đồng; chúng không được lưu làm evidence thực tế. Gate kiểm tra tính nhất quán các trường này, chưa xác thực nguồn adapter hay cách ly thực thi.

Khi có hai cấu hình thực, cần làm lần lượt:

1. Khóa version agent/Harbor, đọc source và tài liệu chính thức của đúng adapter.
2. Triển khai mapping từ profile tới cấu hình agent được khởi tạo; chỉ mở kwargs mà adapter hỗ trợ. Không dùng dictionary tự do để bỏ qua validation.
3. Thu cấu hình hiệu lực, đối chiếu từng trường và prompt content hash; kiểm tra thay đổi quan trọng bị phát hiện.
4. Kiểm định API architecture, egress/isolation, error taxonomy, usage và cost của provider thật. Khai báo policy không thay cho enforcement.
5. Lưu evidence có nguồn và scope cùng manifest model đã đóng băng. Lập executor thật gọi gate và kiểm tra lại trạng thái ngay trước từng dispatch; executor này hiện **chưa triển khai**.
6. Chạy smoke trong ngân sách riêng rồi mới pilot. Không dùng kết quả mô phỏng để qua các bước trên.

Giá provider sẽ được xác minh khi model/provider được chọn. Không có bảng giá giả hay API key mặc định để chạy thử.
