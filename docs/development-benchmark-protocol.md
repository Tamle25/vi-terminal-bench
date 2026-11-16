# Giao thức bản nhỏ development v1

Ngày 13/11/2026. Phạm vi được người dùng chọn: bản nội bộ sáu task B, một model/agent, EN/VI và ba repeat. Task chưa được review độc lập vẫn chạy được trong hai scope mới; manifest giữ `review_status=pending`, tác giả `Codex-assisted` và `development_only=true`. Gate reviewed pilot/phát hành cũ không đổi.

## Scope và điều kiện

`development-smoke` có hai trial B001 EN/VI; `development-batch` có đúng 36 planned trial. Smoke riêng không tính vào batch. Batch cần bằng chứng smoke cùng config/source đã chạy hợp lệ và có terminal tool thật. Manifest được tạo trước, seed 20261113, thứ tự task/ngôn ngữ được lưu; container/history sạch mỗi trial. Một cấu hình model/agent dùng cho mọi repeat và ngôn ngữ; resource/artifact policy lấy từ đúng task.

Model snapshot `gpt-5.4-mini-2026-03-17`, reasoning none, Responses API/function terminal, service tier default, không store/stream, concurrency 1, không automatic retry. Giới hạn: 6 request/trial, 2.048 output token/request, payload 64 KiB, trial 300 giây, command 10 giây, capture 16 KiB mỗi luồng. Mỗi request có claim/request ID trước network. Protocol theo [OpenAI Docs](https://developers.openai.com/api/docs/guides/function-calling), kiểm 13/11/2026.

## Budget và settlement development

Trần pool là 2 USD cho các run benchmark trong ledger. Pool giữ exposure connectivity cũ 0,01 USD và correction margin 0,10 USD; hai khoản giữ này không phải hai charge mới. Ledger riêng ở storage Linux bền vững, không sửa ledger cũ hoặc mở DB mới để reset cap. Nó không quản lý request do ứng dụng khác dùng cùng tài khoản gửi ngoài benchmark.

Reservation mỗi request vẫn dự phòng toàn bộ model maximum input 272.000 token cộng output 2.048 token: **0,213216 USD** theo [giá OpenAI](https://developers.openai.com/api/docs/models/gpt-5.4-mini) kiểm 13/11/2026. Chưa có tokenizer bound mới được giả định từ byte count. Payload byte cap chỉ giới hạn context của agent, không được dùng như chứng minh token count.

Policy `observed-usage-conservative-input-v1` chỉ settlement khi HTTP/model/tier/status/request ID, input/output/total/cache/reasoning usage đều đủ và nhất quán. Toàn bộ input được tính ở giá uncached, output bao gồm reasoning tính một lần. Cache-write fee chưa được mapping hoặc bất kỳ field không hợp lệ sẽ giữ unknown/full reservation và chặn request mới. Các phí chỉ áp dụng text/custom function; không bật built-in tool trả phí.

Usage đã mapping được lưu nguyên receipt; settlement amount và receipt hash là overlay append-only, hoàn phần reservation thừa theo estimate bảo thủ. Đây là **token estimate, chưa phải invoice**; margin vẫn giữ để correction. Invoice revision sau này được ghi riêng và dùng latest revision, không cộng trùng. Nếu charge/exposure vượt bound, lưu bằng chứng và chặn dispatch tiếp, không xóa chi phí đã phát sinh.

Docker chạy local ghi thời gian, CPU/RAM và `compute_cost_status=not_metered`, `compute_cost_usd=null`. USD API pool không tự tính tiền điện/khấu hao máy thành 0 hay giá cloud giả. Nếu chuyển sang compute trả phí phải tạo config/quote/caps và policy phù hợp trước thực thi.

## Artifact, verifier và recovery

Agent không nhận key, `.env`, expected/oracle/test kín hoặc Docker socket. Runtime explicit `desktop-shared-relay-v2` chỉ mở relay tạm tới shared container proxy; root mở socket, workload user thường. Root filesystem read-only; output/tmp là tmpfs có giới hạn. Collector trusted chạy trong container, dừng process model còn lại, stream dữ liệu từ filesystem đang mount rồi pause; không dùng recursive docker cp vì có thể bỏ nội dung tmpfs. Host chỉ giải nén bounded regular files/directories, từ chối link/traversal/device. B002 giữ bytes và tên NFC/NFD/case-distinct; B005 dùng đúng Node/ICU/CLDR trong image task.

Verifier riêng, network none, root read-only và dữ liệu artifact truyền bằng tar stdin có kiểm size/path/type vào tmpfs riêng. Không cần bind mount path Ubuntu vào daemon và không thực thi code agent tạo. Reward do grader xác định; lời model nói hoàn thành không là pass. Trial timeout được ghi agent_timeout/reward 0; transfer/provider/verifier lỗi chưa giải quyết là infra/reward null. Reward 0 hợp lệ không bị retry để tăng điểm. Terminal path và coverage của smoke được kiểm riêng với reward.

Controller ghi outcome vào ledger kèm hash trước xuất file. Report đối chiếu file với ledger outcome và frozen identity; sửa reward trong JSON không tự đổi bảng điểm. Có thể khôi phục outcome đã commit nhưng chưa ghi file mà không gọi model. `resume-unstarted` chỉ tiếp tục trial chưa được claim; partial provider/tool state không auto replay, mọi request/attempt cũ được giữ.

## Chấm và công bố nội bộ

Mỗi task/language lấy trung bình ba repeat, rồi macro-average qua sáu task. Hiện mỗi nhóm năng lực có một task nên cùng giá trị với điểm task tương ứng. Delta VI−EN tính điểm phần trăm trên coverage khớp; thiếu/infra giữ rõ và chưa gọi run hoàn tất. Không lấy best-of-three. CI để null do một family/nhóm, không xem repeat/bản dịch là family mới.

Report gồm normalized JSONL, CSV UTF-8 BOM, JSON summary và Markdown. Có coverage, task/EN/VI, delta, token/duration, conservative token cost và invoice/compute status. Nhãn development/unreviewed được giữ ở mọi báo cáo; không dùng kết quả này thay reviewed pilot hoặc bản phát hành chính thức.
