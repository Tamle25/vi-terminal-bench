# Dùng executor giai đoạn 5

Executor hiện chỉ validate cấu hình hoặc chạy adapter fixture cục bộ. Chưa hỗ trợ model/provider thật; không nhập API key để “thử” đường này.

## Readiness thực hiện tại

Chạy tại root repo bằng Python 3.12.16 trong WSL đã chuẩn bị. Dùng tên report mới để giữ nguyên bằng chứng cũ:

```bash
PY=/tmp/vi-terminal-bench-runtime/offline-tests/bin/python
"$PY" scripts/model_executor.py \
  --scope native-pilot --output /tmp/stage5-readiness-new.json
```

Exit 2 là dự kiến vì thiếu đầu vào và binding provider. `--mode model` cũng không dispatch, không đọc secret hoặc tạo execution state. Report hiện tại là `reports/stage5-model-readiness-current.json`; bản khởi tạo trước đó được giữ riêng.

## Bộ test offline

```bash
# Có thể tải Python nếu /tmp đã mất; không cần Docker hoặc API.
# Chọn output chưa tồn tại. Script từ chối ghi đè bằng chứng.
bash scripts/setup-offline-tests.sh reports/my-new-offline-tests.json
```

Script không còn ghi mặc định vào report stage4. Nguồn được copy có kiểm tra hash sang filesystem Linux để tránh đọc lặp qua mount Windows; report lưu hash input, và các file gốc được đối chiếu lại sau kiểm định. Các test dùng fixture có nhãn riêng, bao gồm scope smoke/pilot, gate sau preview, receipt/cost chưa rõ, crash qua process, tranh claim C1 và accounting trong trial nhiều request.

## Tạo một run fixture mới

Fixture helper dành cho kiểm định local. Input prompt phải nằm trong workspace; raw state nên ở filesystem Linux. Không dùng tên `model-smoke` của scope mục tiêu để gọi đây là smoke model thật.

```bash
export VI_FIXTURE_INPUT=$(mktemp -d "$PWD/build/my-stage5-input-XXXXXX")
STATE=$(mktemp -d /tmp/vi-stage5-fixture-XXXXXX)
"$PY" - <<'PY'
import os, sys
from pathlib import Path
sys.path.insert(0, 'scripts')
from executor_fixtures import fixture
fixture(Path.cwd(), Path(os.environ['VI_FIXTURE_INPUT']), requests=2)
PY

"$PY" scripts/model_executor.py --mode offline-fixture \
  --context "$VI_FIXTURE_INPUT/context.json" \
  --manifest "$VI_FIXTURE_INPUT/manifest.json" \
  --settings "$VI_FIXTURE_INPUT/effective-settings.json" \
  --state-dir "$STATE" --max-attempts 1 \
  --output "$STATE/first-process.json"
# Exit 2 nếu còn trial chưa thực hiện; resume giữ nguyên input, settings và state.
"$PY" scripts/model_executor.py --mode offline-fixture \
  --context "$VI_FIXTURE_INPUT/context.json" \
  --manifest "$VI_FIXTURE_INPUT/manifest.json" \
  --settings "$VI_FIXTURE_INPUT/effective-settings.json" \
  --state-dir "$STATE" --output "$STATE/resumed-process.json"
```

Không thay manifest/profile/policy/budget/source rồi tiếp tục ledger cũ. Attestation fixture mặc định hết hạn sau 300 giây; khi cần refresh trong kiểm định, chỉ cập nhật observation cùng run/snapshot/stable profile. Không chuyển fixture attestation thành runtime thực bằng đổi nhãn.

`--max-attempts` giới hạn số attempt có gửi request trong tiến trình, không tạo repeat mới. Chi phí trong output là micro-unit SIM_USD, `cost_usd=null`. Một trial có thể tạo nhiều request; xem cả `requests.jsonl` lẫn raw attempt và tổng ledger.

## Archive và khôi phục

Chỉ archive sau khi đóng process/connection, bao gồm cả hai DB, raw, event, request ledger và input/provenance. Nếu backup khi đang ghi cần cơ chế backup nhất quán, không copy riêng main SQLite file bỏ qua WAL.

Archive bàn giao giai đoạn 5 đã được mở lại để kiểm state/receipt/request và số lượt gọi. Đây là kiểm định phục hồi dữ liệu, chưa phải bảo đảm có thể dispatch từ đường dẫn fixture đã di chuyển: profile hash chứa đường dẫn system prompt trong workspace. Để tái lập mới, tạo input/run mới theo hướng dẫn; để tiếp tục run cũ phải phục hồi đúng contract và input của run đó.

`stage5_validate_offline.py` tạo bằng chứng integration ở các đích cố định và từ chối ghi đè. Không chạy lại vào report đã có; chỉ tạo run/report/archive mới khi thay đổi đường thực thi cần kiểm lại. Chưa có lý do chạy thêm 72 trial giả chỉ để tăng số liệu.
