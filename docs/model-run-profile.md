# Model profile và dry-run giai đoạn 3

Chưa chọn agent/model, ngân sách hoặc credentials. Template có giá trị null có chủ đích: [model-pilot.template.json](../configs/model-pilot.template.json). Không điền model hoặc tiền thay người phụ trách.

```bash
python3 scripts/model_dry_run.py --profile configs/model-pilot.template.json --output reports/my-model-preview.json
```

Công cụ không gọi subprocess, provider API hoặc đọc biến môi trường chứa secret. Nó tạo 72 planned trial ID duy nhất (6 B × EN/VI × 3 repeat × 2 cấu hình), hash payload/instruction/config và liệt kê đầu vào còn thiếu. `kind=offline-dry-run-not-executable`, `ready_for_model_calls=false` luôn đúng: đây là preview, không phải quyền chạy.

## Cần người phụ trách chốt

- Hai cấu hình: agent/version, model/provider/endpoint, effort (hoặc `not-applicable`), prompt Markdown, token/turn/time, kiến trúc và tên biến credentials.
- Trần inference, compute và smoke riêng; concurrency và điều kiện dừng.
- Reviewer chấp nhận snapshot task, runtime/network profile đủ điều kiện và mapping agent-specific đã được kiểm định.

Chỉ lưu tên biến credentials, không lưu giá trị. Từ chối unknown fields, URL chứa user/password/query secrets và kwargs chưa có mapping an toàn. Không kiểm chứng API key bằng cách in key hoặc gọi API trong dry-run.

## Fingerprint và mapping

Fingerprint preview bao gồm cấu hình, hash nội dung system prompt và concurrency; planned task chứa canonical payload/instruction hash. `check_effective` kiểm hợp đồng dữ liệu thuần, có test phát hiện đổi model/endpoint/version/effort/budget. Chưa có mapping production cho một agent cụ thể; không coi helper này là bằng chứng effective Harbor config đã được xác minh.

Khi có agent thật, cần mapping từ config thực tế, kiểm endpoint, prompt, kwargs, effort, resource overrides, timeout, token/turn và network attestation. Unknown provider error phải được phân loại tường minh; rate limit không tự thành model fail, null reward không được ép thành 0, retry phải giữ planned identity và mọi attempt. Các test theo provider/agent thực tế còn deferred.

## Kiến trúc và mạng

Hai phương án cho cấu hình cụ thể: host agent thao tác sandbox offline hoặc agent cài sẵn có egress được kiểm soát. Chưa chọn phương án thay người phụ trách. Verifier luôn offline và không nhận API credentials. Không suy ra allowlist hoạt động từ field TOML.

Relay WSL giai đoạn 3 là đường Docker control plane cục bộ, không phải đường API model và không phải sandbox egress policy. Nó chỉ tồn tại trong lệnh, socket mode0600, target chạy dưới user thường; cần WSL root để tiếp cận socket Desktop được bảo vệ. Không tự coi endpoint relay là runtime profile đã phê duyệt cho model run.

Runner `execute_validation_plan.py` vẫn chỉ cho oracle/nop. Preview model không được đưa vào runner đó, và không có model executor được bật bởi template.
