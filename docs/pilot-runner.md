# Vận hành runner mô phỏng

`scripts/pilot_runner.py` chỉ thực thi fake provider cục bộ. Mặc định `--mode simulation`; `--mode model` từ chối trước khi đọc plan hoặc tạo state. Không có model executor, secret loader hay API client trong runner này.

## Chạy và resume

Các lệnh dưới đây chạy trong WSL, từ root repo. Dùng Python đã được chuẩn bị bằng `bash scripts/setup-offline-tests.sh`; script này cần `uv` và có thể tải Python 3.12.16, không cài Harbor hay gọi Docker.

```bash
PY=/tmp/vi-terminal-bench-runtime/offline-tests/bin/python
STATE=$(mktemp -d /tmp/vi-pilot-simulation-XXXXXX)
"$PY" scripts/pilot_runner.py \
  --plan reports/stage4-simulation-run.json \
  --scenarios reports/stage4-simulation-scenarios.json \
  --state-dir "$STATE" --max-dispatches 11
# Chạy tiếp cùng plan, fixture và state; hoàn tất rồi gọi lại không gửi thêm.
"$PY" scripts/pilot_runner.py \
  --plan reports/stage4-simulation-run.json \
  --scenarios reports/stage4-simulation-scenarios.json \
  --state-dir "$STATE"
```

Giữ state trên filesystem Linux. Các report stage4 được bàn giao là bằng chứng đã có; không chạy lại `stage4_validate_offline.py` vào cùng output vì script chủ động từ chối ghi đè bằng chứng. Nếu tạo thí nghiệm mới, dùng run ID và đích report/archive mới trước khi lập plan. Không sửa snapshot/profile/budget trong plan rồi tiếp tục ledger cũ; hash drift bị từ chối.

Mỗi state có `ledger.sqlite3`, `fake-provider.sqlite3` và `export/` gồm raw attempt, normalized trials, events, summary. Đóng các process/connection trước khi đóng gói cả thư mục; nếu dùng online backup phải backup nhất quán cả hai database. Không copy riêng file `.sqlite3` trong lúc WAL đang được ghi. Archive đã bàn giao chứa state đóng sau các child process và đã được mở kiểm tra sau giải nén.

## Dispatch, retry và gián đoạn

SQLite dùng WAL, `synchronous=FULL` và transaction `BEGIN IMMEDIATE`. Reservation được ghi trước submit; compare-and-swap phase `reserved → submitted` chỉ cho một worker nhận attempt. Lease mặc định 30 giây. Scheduler chạy tuần tự với seed cố định; kiểm tra tranh chấp hai worker là kiểm tra bảo vệ ledger, không phải bằng chứng runtime model concurrency 2 đã đạt.

| Tình huống | Xử lý |
|---|---|
| Chết sau reserve | Resume có thể claim reservation chưa submit |
| Chết sau submit | Đợi lease; chuyển uncertain và lookup, không gửi lại khi chưa có receipt |
| Fake provider đã lưu receipt, harness chưa ghi kết quả | Reconcile receipt, không dispatch lại |
| Đã completed/agent failure | Giữ kết quả, không retry để đổi reward |
| Lỗi infra/verifier đã phân loại | Tối đa ba attempt tổng cộng; giữ mọi attempt và phí |
| Unknown provider hoặc receipt thiếu | Giữ uncertain và dừng dispatch mới |
| Đã biết reward nhưng thiếu cost | Giữ reward trong normalized, giữ reservation phần chưa biết; run chưa hoàn tất tài chính |

`confirm_not_submitted()` chỉ nhận receipt giả `simulation-authoritative-not-received` kèm lookup không có request. Đây là đặc tính fake provider. Không suy diễn từ “không tìm thấy” ở provider thật rằng request chưa nhận/charge; không có bảo đảm idempotency cho provider thật từ các test này.

## Ledger và output

Đơn vị số nguyên micro-unit thuộc **SIM_USD**, nguồn `synthetic-fixture-v1-not-provider-pricing`. Đây không phải USD thật. Inference/compute có reservation và cap riêng; smoke thật phải dùng scope/budget riêng ở executor tương lai.

Mọi attempt, kể cả lỗi, giữ phí đã biết. Giá trị chưa rõ lưu null, exposure dùng reservation cho phần null, không tự hoàn tiền. Khi có uncertain, runner chặn dispatch mới. Nếu receipt vượt reservation/cap, ledger lưu đúng số quan sát và sự kiện overrun rồi chặn công việc kế tiếp; nó không thể đảo ngược phí đã phát sinh. Chỉ reservation chưa submit mới được cancel với actual cost 0.

Normalized có `data_origin=simulation`, `cost_usd=null`; synthetic cost ở trường riêng. Aggregate bắt buộc plan `kind=simulation`, từ chối trộn với model và gắn `result_kind=simulation-not-model-evaluation`. Score số học trong file simulation chỉ dùng kiểm tra pipeline, không công bố như năng lực model.

## Kiểm tra readiness hiện tại

```bash
"$PY" scripts/pilot_readiness.py \
  --profile configs/model-pilot.template.json \
  --runtime-profiles configs/runtime-profiles.json \
  --output /tmp/vi-pilot-readiness-now.json
```

Exit code `2` khi thiếu điều kiện là kết quả dự kiến; `0` nghĩa là bằng chứng dữ liệu nhất quán, không phải token cấp quyền hay lệnh tự chạy model. Xem [readiness bàn giao](../reports/stage4-readiness.md) và [schema](pilot-state-schema.md).
