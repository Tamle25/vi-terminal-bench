# Host agent terminal — giai đoạn 10

Đã triển khai `vi-host-terminal/0.1` theo [kế hoạch](../Plan/plan-giai-doan-10.md). Đây là implementation có kiểm offline; Docker integration và model tool calling thực chưa được kiểm trên môi trường hiện tại. Controller mặc định preview; đường execute có precheck, chưa có approved input cho smoke thật.

## Điểm nối và lựa chọn

Harbor được khóa `0.25.0` trong `pyproject.toml`/`uv.lock`; các task dùng môi trường và verifier riêng. Executor hiện tại là fixture với schema pilot hai cấu hình, guard model còn đóng và ledger SIM_USD. Chưa có bằng chứng hook của agent Harbor cài đặt hiện tại bảo đảm accounting từng request. Vì vậy triển khai một host loop tối thiểu bằng stdlib, tái sử dụng hợp đồng snapshot/review/attestation; không thay guard cũ hoặc giả cấu hình so sánh thứ hai. Source agent Harbor đang cài chưa được kiểm định trong giai đoạn này.

| Thành phần mới | Vai trò |
|---|---|
| `scripts/terminal_agent_v1.py` | Tool schema, history, request/context limits, RealGate, OpenAI client và loop |
| `scripts/terminal_sandbox_v1.py` | Docker argv, quan sát policy thật, giới hạn capture, pause/copy và giải nén artifact an toàn |
| `scripts/terminal_verifier_v1.py` | Verifier riêng, mapping exit/reward và normalized record |
| `scripts/usd_ledger_v1.py` | Pool/run/trial/request/tool claim, reservation, estimate và invoice revision |
| `scripts/terminal_provider_worker_v1.py` | Một HTTP request trong process có thể dừng theo deadline, credential chỉ qua stdin pipe |
| `scripts/terminal_smoke_v1.py` | Prepare image provenance, freeze/precheck, lifecycle hai trial và cleanup |
| `scripts/stage10_prepare.py` | Kiểm lịch sử, ledger connectivity read-only và tạo hồ sơ review pending |
| `scripts/stage10_validate_offline.py` | Tích hợp fixture trên bản sao Linux công khai, không key/model/Docker |

## Giao thức agent

Host giữ credential và gọi HTTPS OpenAI Responses trực tiếp; không SDK retry, redirect, base URL override hoặc proxy từ môi trường. Chỉ có function `terminal(command)` dạng JSON schema strict, không tool trả phí tích hợp. `parallel_tool_calls=false`; controller xử lý tuần tự nếu nhận nhiều call. Chỉ tên/arguments hợp lệ mới tới backend, duplicate JSON key bị từ chối.

History chứa instruction gốc và toàn bộ response output, gồm reasoning item khi có, rồi `function_call_output` khớp `call_id`. Không dùng previous response hay hội thoại chung giữa EN/VI. Giới hạn payload JSON 16 KiB được kiểm lại sau mỗi tool output; không tự cắt instruction hoặc âm thầm đổi policy để chạy tiếp. Transcript có request intent, receipt, tool intent/result và stop reason; redaction trước khi ghi.

Thiết kế theo [OpenAI Docs về function calling](https://developers.openai.com/api/docs/guides/function-calling), kiểm ngày 13/11/2026. Model giữ `gpt-5.4-mini-2026-03-17`, reasoning `none`, service tier `default`, store/stream false. Khả năng gọi tool của tài khoản vẫn chưa thử thực tế; response text giai đoạn 9 không thay bằng chứng đó.

## Giới hạn và reservation

Draft có 4 request/trial, 1.024 output token/request, concurrency 1, trial 300 giây, lệnh 10 giây, stdout/stderr tối đa 16 KiB mỗi luồng. Timeout command được thực thi trong container bằng wrapper Python; process group bị dừng cả khi shell chính đã kết thúc. HTTP chạy trong worker riêng; parent dùng timeout tối đa 30 giây và kill process group khi hết hạn, nên không chỉ dựa vào socket timeout cho DNS/slow stream. Credential qua private stdin pipe, không argv/env/file/stderr. Trial deadline được kiểm lại ở ranh giới gate/request/tool; container có TTL 360 giây để không chạy vô hạn khi controller crash. Cleanup/verifier là pha có bound riêng, không tính CLI kết thúc đúng 300 giây. Thực thi các bound này với backend/container/provider thật vẫn chưa được kiểm.

Không dùng số token của prompt đầu để ước tính toàn bộ vòng lặp. Dự phòng mỗi request theo **272.000 input token**, là maximum input công bố cho model, cộng 1.024 output token; payload thực vẫn bị giới hạn 16 KiB. Đây là bound giá thận trọng của cả model, không tuyên bố đã đếm chính xác token của JSON/tool schema. Với [giá model](https://developers.openai.com/api/docs/models/gpt-5.4-mini) kiểm ngày 13/11/2026, reservation là **0,208608 USD/request** và tối đa **1,668864 USD/tám request**. So với draft plan ban đầu tám request/trial, giảm xuống bốn để giữ mức inference đề xuất dưới 2 USD.

## Sandbox và verifier

Model command được truyền như một argv cho wrapper trong `docker exec`; không đưa sang shell host. Container được kiểm bằng ID 64 hex, image ID và label run, mạng `none`, không host bind/device, cap drop ALL, no-new-privileges, CPU/RAM/PID theo config. Root filesystem read-only, `/tmp` và `/app/output` là tmpfs 16 MiB mỗi mount; input B001 không thay đổi được. Controller reserve compute và lấy claim owner trước create/start, chỉ chuyển owner token trong process hiện tại sang loop. Các giới hạn này là cấu hình agent mới, cần kiểm bằng container thực và giữ giống nhau cho EN/VI.

Sau loop, backend pause container để dừng writer và giữ dữ liệu tmpfs rồi copy `/app`. Không stop trước transfer vì có thể mất tmpfs. Host chỉ nhận thư mục/file thường trong tar có bound byte/file count; từ chối absolute path, traversal, symlink, hardlink/device và destination có sẵn. Giữ bytes/tên Unicode trên filesystem Linux. Cleanup chỉ container đã kiểm label/ID của run.

Verifier chạy image riêng có grader/expected, network none, mount artifact read-only và không key/socket. Grader chỉ đọc dữ liệu, không thực thi code agent. Reward 0 do kết quả sai là quan sát hợp lệ; lỗi verifier cho reward null. Normalized record phân biệt origin, failure class, stop reason, terminal path observed và trạng thái billing. Record fixture không trở thành benchmark chỉ vì grader trả reward.

## Gate và trạng thái hiện tại

RealGate đối chiếu approved config, source/prompt/tools, snapshot, review human, attestation, sandbox policy thực, caps/run contract/pool và exposure connectivity liên kết receipt/DB cũ read-only. Đây là kiểm hợp đồng local, không xác thực mật mã danh tính reviewer hay quyền chi do nhà cung cấp cấp. Việc nhập authorization evidence phải theo quyết định thực của chủ dự án.

Chưa có reviewer theo trả lời của người dùng; Docker socket/CLI integration trong Ubuntu-22.04 không hoạt động ở lần chẩn đoán này. Draft giữ runtime/caps/authorization/ledger path/compute quote null; không có approved run hoặc attestation mới. Library và controller CLI đã có kiểm offline, chưa nghiệm thu bằng container/model thực. Không có run model, container hoặc terminal smoke thật trong giai đoạn này.

```powershell
# Preview: không đọc key, không gọi mạng.
python scripts/terminal_agent_v1.py
python scripts/terminal_smoke_v1.py
```

Controller có `--prepare-images` trên runtime đạt, đóng băng source/task label của hai image riêng; `--freeze` kiểm reviewed config/attestation/images trước ghi contract; `--execute` dựng lại contract và gate. Các mode này không tự sinh review/authorization. `--execute` với draft hiện tại bị từ chối trước tạo container/key. Shared ledger phải ở path Linux bền vững được approved config đóng băng, ngoài `/tmp` và `/mnt`; đổi output directory không tạo budget mới. Không tự resume run đã có claim.

Xem [run spec](../reports/stage10-run-spec.md) và [recovery](terminal-agent-recovery.md) cho các phần phải hoàn tất trước thực thi.
