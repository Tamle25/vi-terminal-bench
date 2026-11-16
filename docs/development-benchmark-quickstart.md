# Chạy bản nhỏ sáu task B

Runtime được chọn là `desktop-shared-relay-v2`: Docker Desktop hoạt động nhưng proxy riêng của Ubuntu có thể timeout. Relay tạm trỏ shared container proxy đã kiểm, không sửa socket hệ thống hoặc restart dịch vụ. Root chỉ giữ relay mode 0600; benchmark chạy dưới user `tamle`. Artifact và ledger ở filesystem Linux. Credential nằm trong `.env` root, không source vào shell hoặc truyền key qua argv.

Từ PowerShell tại root repo, chuẩn bị Python và tạo hàm gọi CLI qua runtime đã chọn:

```powershell
# Bootstrap/preview, không đọc key hoặc gọi model.
wsl.exe -d Ubuntu-22.04 -e bash scripts/development-benchmark.sh plan
$benchRepoLinux = (wsl.exe -d Ubuntu-22.04 -e wslpath -a (Get-Location).Path).Trim()
$benchPythonLinux = '/home/tamle/vi-terminal-bench-stage11/venv/bin/python'
function bench {
    & wsl.exe -d Ubuntu-22.04 -u root -e $benchPythonLinux `
        "$benchRepoLinux/scripts/with_runtime_proxy_v2.py" `
        --user tamle --timeout 14400 -- /usr/bin/taskset -c 0 $benchPythonLinux `
        "$benchRepoLinux/scripts/dev_benchmark.py" @args
    if ($LASTEXITCODE -ne 0) { throw "Benchmark exit code: $LASTEXITCODE" }
}
```

Các lệnh `bench` dưới đây dùng lại hàm này. Controller ghim CPU 0 để tránh clock/attestation jitter đã quan sát trong WSL; quota agent container vẫn 1 CPU theo task. Không nới kiểm tra thời gian hoặc bỏ gate. Khi command kết thúc, relay tự dọn; không có daemon root mới được cài. Scope development cho phép pending review, các gate runtime/source/budget/credential vẫn hoạt động.

## Preview và kiểm backend

```powershell
# Chỉ lập danh sách 36 trial, không đọc key/gọi API.
bench plan
# Build task/verifier images, oracle + no-op cả sáu task; không gọi model.
bench validate `
  --output /home/tamle/vi-terminal-bench-stage11/validation-final
```

Chọn output mới nếu đã có evidence; không ghi đè report cũ. Các ví dụ sau dùng `validation-final/validation.json`; thay bằng đường dẫn của lần validation đã đạt trên source hiện tại.

## Smoke EN/VI

```powershell
bench plan --scope development-smoke `
  --run-id my-development-smoke `
  --validation /home/tamle/vi-terminal-bench-stage11/validation-final/validation.json `
  --output /home/tamle/vi-terminal-bench-stage11/my-smoke-plan.json
bench run `
  --plan /home/tamle/vi-terminal-bench-stage11/my-smoke-plan.json
```

Lệnh run có gọi model thật và dùng shared pool tối đa 2 USD theo [config](../configs/development-benchmark.json), tính cả hold/exposure các run trước. Review pending được phép trong scope development. Giá/token/config/validation/source thay đổi sẽ làm gate từ chối, không tự fallback. Không đổi run ID để né state uncertain hoặc ngân sách.

## Batch 36 trial

Run smoke in ra một đường `.../runs/my-development-smoke/report-<id>`. Dùng đúng `summary.json` của report đạt technical smoke cho bước kế tiếp.

```powershell
bench plan --scope development-batch `
  --run-id my-development-batch `
  --validation /home/tamle/vi-terminal-bench-stage11/validation-final/validation.json `
  --smoke '/home/tamle/vi-terminal-bench-stage11/runs/my-development-smoke/report-<id>/summary.json' `
  --output /home/tamle/vi-terminal-bench-stage11/my-batch-plan.json
bench run `
  --plan /home/tamle/vi-terminal-bench-stage11/my-batch-plan.json
```

Thay `<id>` bằng ID thật trước khi chạy, hoặc quote đường dẫn nếu dùng shell. Run giữ config/snapshot/source/images cố định; sáu task × EN/VI × ba repeat = 36 planned trial. Mỗi trial có folder riêng chứa trajectory, artifact, attestation và outcome. Reward 0 là kết quả hợp lệ; lỗi hạ tầng/uncertainty sẽ dừng để điều tra.

## Tiếp tục và dựng lại report

```powershell
# Chỉ tiếp tục trial chưa gửi của run đã có, không replay partial state.
bench resume-unstarted `
  --plan /home/tamle/vi-terminal-bench-stage11/my-batch-plan.json
# Chỉ đọc outcome/ledger và xuất report mới, không đọc key hoặc gọi API.
bench report `
  --plan /home/tamle/vi-terminal-bench-stage11/my-batch-plan.json `
  --output /home/tamle/vi-terminal-bench-stage11/reproduced-report
```

Các file chính: `results.md`, `summary.json`, `trials.csv`, `normalized.jsonl`. `complete=true` cần đủ valid trial; xem riêng `technical_smoke_passed` với scope smoke. Cost là estimate, invoice chưa có; compute local not-metered. Một command run điều phối toàn bộ manifest đã freeze; không cần gọi thủ công từng task.

Config mặc định và profile là của workspace này. Trên máy khác cần chọn storage/profile phù hợp và đóng băng run mới; không sửa config rồi tiếp tục manifest cũ. Xem [giao thức development](development-benchmark-protocol.md) trước diễn giải điểm hoặc xử lý state uncertain.

## Lần chạy đã nghiệm thu

`stage11-development-001` đã đủ 36/36 trial hợp lệ, 35 pass. [Kết quả](../reports/development-benchmark-results.md), [JSON](../reports/development-benchmark-summary.json) và [CSV](../reports/development-benchmark-trials.csv) có sẵn. Có thể gọi `bench report` với `/home/tamle/vi-terminal-bench-stage11/stage11-batch-plan.json` và một output mới để dựng lại kết quả, không tốn request model.

Nếu gặp `DISPATCH_BLOCKED`, không tự reset state hoặc gửi lại request. Công cụ `scripts/development_reconcile.py` chỉ xử lý một intent có bằng chứng đúng loại **CredentialError trước HTTP worker**, chưa có tool/receipt provider, sau backup và audit. Timeout/HTTP error/unknown không đủ điều kiện. Lần nghiệm thu đã giữ checkpoint và một cancellation như vậy; không chạy lại lời giải reward 0. Chỉ dùng recovery sau khi đọc [audit](../reports/stage11-pre-dispatch-cancellation.json) và xác minh đúng điều kiện của run cần phục hồi.
