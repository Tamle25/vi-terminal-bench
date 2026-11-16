# Phát triển và kiểm định

## Cập nhật giai đoạn 3

Xem [runtime diagnosis](../reports/runtime-diagnosis.md), [smoke stability](../reports/runtime-stability.md) và [readiness hiện tại](../reports/stage3-readiness.md). Default WSL socket có thể timeout dù Windows Docker khỏe; không coi một probe thành công là hết lỗi. Preflight mới giới hạn CLI10 giây và ghi từng bước; file capture và owned process-group cleanup tránh descendant giữ pipe vô hạn.

Đã kiểm định workaround scoped Unix relay, không restart dịch vụ hay sửa socket hệ thống. Trong PowerShell, khi người vận hành chủ động chọn profile local này:

```powershell
wsl -d Ubuntu-22.04 -u root -- /tmp/vi-terminal-bench-runtime/venv/bin/python '/mnt/d/Xay dung tuong tu bo Terminal-Bench/scripts/with_runtime_proxy.py' --user tamle --timeout 60 -- /tmp/vi-terminal-bench-runtime/venv/bin/python '/mnt/d/Xay dung tuong tu bo Terminal-Bench/scripts/preflight.py' --jobs-dir /tmp/vi-terminal-bench-runtime/jobs
```

Lệnh bên trong chạy dưới tamle, không phải root; socket relay mode0600, command-only. Đường distro proxy hiện cố định cho Ubuntu-22.04, không phải giải pháp portable mọi máy. Sau lệnh relay tự đóng; default integration không bị thay. Đây là Docker control plane, không cho phép API model hoặc container egress. Không tự thêm wrapper này vào model run chưa được cấu hình.

Dry-run model không gọi API:

```bash
python3 scripts/model_dry_run.py --profile configs/model-pilot.template.json --output reports/my-model-preview.json
```

Xem [profile contract](model-run-profile.md), [review guide](review-guide.md) và [private test design](private-test-design.md). Runner oracle/nop vẫn từ chối model plan; preview thiếu đầu vào luôn không executable.

## Môi trường

Workspace ở Windows; chạy harness trong WSL2 Ubuntu và Docker Linux. Python của task là 3.12.12, Unicode database 15.0.0; image được khóa bằng digest trong Dockerfile. Harness là Harbor 0.25.0, dependency pin trong uv.lock. Host Python 3.11 có thể chạy một số công cụ stdlib nhưng không phải runtime đánh giá.

Trong WSL, chuyển tới thư mục dự án rồi chạy:

```bash
bash scripts/setup-wsl.sh
```

Script dùng uv từ PATH hoặc `~/.local/bin`; tạo Python 3.12.16/venv/cache trong `/tmp/vi-terminal-bench-runtime`, tránh hạn chế symlink/executable trên ổ Windows. Script yêu cầu uv.lock không đổi bằng `uv sync --locked`. Nếu vùng tạm bị dọn, chạy setup lại. Phiên bản uv đã dùng để dựng môi trường: 0.13.7.

**Jobs và artifact bắt buộc nằm trên filesystem Linux.** Nếu lưu trên ổ Windows, tên `Báo cáo.txt` và `báo cáo.txt` có thể bị gộp lúc transfer, gây false negative. Wrapper `harbor-wsl.sh` mặc định dùng `/tmp/vi-terminal-bench-runtime/jobs` và từ chối jobs-dir dưới `/mnt`. Dùng thư mục Linux bền vững ngoài vùng tạm nếu vận hành dài hạn và được cấp quyền. Sao lưu artifact bằng tar từ Linux trước khi chép sang Windows; không chép cây file thô có tên nhạy Unicode.

## Kiểm tra cấu trúc và phép tính điểm

```bash
/tmp/vi-terminal-bench-runtime/venv/bin/python scripts/validate_dataset.py --harbor
/tmp/vi-terminal-bench-runtime/venv/bin/python -m unittest discover -s scripts/tests -v
```

## Kiểm định verifier

Chạy controls trong image B005 để có đúng Node/ICU, không dùng Node tùy ý trên host. Đây là kiểm định cục bộ, không phải model evaluation. Trong WSL tại root repo:

```bash
docker build -t vi-terminal/b005-runtime:0.1.0 tasks/b005-vietnamese-collation/environment
docker run --rm --network none \
  --mount "type=bind,src=$PWD,dst=/repo,readonly" \
  --mount "type=bind,src=$PWD/reports,dst=/repo/reports" \
  --workdir /repo vi-terminal/b005-runtime:0.1.0 \
  python scripts/validate_controls.py --output reports/my-controls.json
```

`validate_controls.py` tạo fixture trong thư mục tạm Linux mới cho từng ca, lấy hooks từ registry tường minh, không fallback task. Thêm `--task b003-windows1258` để chọn phần cần kiểm tra. Bằng chứng M1 giữ ở reports/controls.json; sáu task ở reports/native-six-controls.json. Không ghi đè báo cáo cũ khi sửa task.

## Chạy xuyên suốt qua Harbor

Tên job phải mới cho mỗi đợt; không ghi đè kết quả cũ:

```bash
bash scripts/run_native_validation.sh oracle my-new-native-six
bash scripts/run_native_validation.sh nop my-new-native-six
```

Sáu task: oracle phải đạt reward 1 ở 18/18 trial, nop đạt reward 0 ở 6/6. Script preflight, lập run manifest trước, chạy mỗi repeat thành một job -k1 và nhập kết quả theo task/job đã khai báo, không suy repeat từ tên thư mục. Plan/job đã tồn tại sẽ bị từ chối; cần run ID mới. Runner chỉ hỗ trợ oracle/nop, không gọi API model.

Verifier riêng chỉ đọc artifact, không chạy submission. Compose tắt mạng tĩnh; TOML policy public không kích hoạt backend egress động. Trước model run cần cấu hình agent/API phù hợp; không dùng cấu hình offline này một cách máy móc.

Xuất báo cáo kiểm định nhỏ vào repo thay vì sao chép raw artifact qua Windows:

```bash
/tmp/vi-terminal-bench-runtime/venv/bin/python scripts/report_harbor_validation.py --job /tmp/vi-terminal-bench-runtime/jobs/my-new-native-six-oracle-validation-vi-r1 --agent oracle --expected-trials 6 --output reports/my-oracle-r1.json
```

`report_harbor_validation.py` chỉ dành cho oracle/nop, không phải adapter bảng điểm model. Không upload hoặc publish bằng Harbor trong giai đoạn này.

## Tạo dataset theo ngôn ngữ

```bash
python3 scripts/materialize_variants.py --language vi --output build/dev-vi
python3 scripts/materialize_variants.py --language en --output build/dev-en
```

Output phải chưa tồn tại để tránh xóa thay đổi hoặc ghi đè snapshot. Script giữ nguyên payload ngoài instruction và ghi hash trong variant-manifest.json. Bản mặc định task/instruction.md phải trùng prompts/<id>/vi.md. Sửa prompt cần đồng bộ instruction mặc định trước validate.

## Tổng hợp model trial sau này

```bash
python3 scripts/aggregate_results.py normalized-trials.jsonl --run-plan my-run.json --output reports/results.json --csv reports/trials.csv
```

Input theo `evaluation-protocol.md`. Adapter Harbor0.25.0 đã kiểm định theo profile development; model profile ngoài điều kiện hiện tại cần kiểm tra thêm. Run plan phát hiện thiếu cả configuration. CI family-bootstrap trả null nếu thiếu replication/coverage; native-six có một family/skill nên chưa có CI B đủ cơ sở. Không đưa control runs vào bảng điểm model.

## Review và phát hành

Sáu task đang development; review vẫn pending, giấy phép phát hành chưa quyết định. Xem reports/native-six-validation.md, reports/pilot-readiness.md và docs/review-guide.md. Hai outlier pha verifier repeat đầu cần được điều tra trước pilot. Không dùng oracle để so model.

Cuối phiên kiểm định có Docker CLI WSL timeout dù Docker Windows phản hồi. Preflight giới hạn probe 30 giây và ghi ready=false/exit 2; không tiếp tục chạy khi guard này fail. Cần xác minh WSL/Docker integration và đường CLI trước run mới, không restart dịch vụ dùng chung một cách tự động.

B005 thêm Node22.14.0/ICU76.1/CLDR46.0 từ image khóa digest, hiện Linux amd64. Task.checksum của Harbor đang deprecated; dùng được với 0.25.0 đã khóa, cần chuyển sang durable lock digest trước khi nâng harness.
