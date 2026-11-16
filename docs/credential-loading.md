# Credential loader theo process — giai đoạn 8

Cập nhật 13/11/2026. Đã có loader, redaction và kiểm source artifact bằng fixture. Chưa có agent/provider binding gọi API thật; các executor model cũ vẫn giữ guard validation-only.

Theo [OpenAI Docs về SDK](https://developers.openai.com/api/docs/libraries), SDK đọc `OPENAI_API_KEY` từ environment. Repo dùng một bước nạp tường minh trước khi cấp credential cho process/client được chọn; lưu `.env` chưa tự nạp biến vào runtime. OpenAI cũng hướng dẫn giữ key bí mật và cấp phía server qua environment/secret manager trong [Authentication](https://developers.openai.com/api/reference/overview#authentication).

## Nạp credential

`scripts/scoped_credentials.py` cung cấp `credential_scope()` dạng context manager. Hàm không import SDK, gọi network hoặc sửa `os.environ` toàn cục.

| Tham số/hành vi | Hợp đồng hiện tại |
|---|---|
| `mode` | Chỉ `runtime`; preview/dry-run bị từ chối trước khi đọc nguồn credential |
| `target` | `host-agent` hoặc `model-api-client`; verifier/task/build/container agent chưa được hỗ trợ |
| `gate` | Callable do binding thực cung cấp; phải trả đúng boolean true trước khi nạp và khi truy cập credential |
| `environment` | Mapping được cấp tường minh; nếu không truyền, đọc environment hiện tại sau gate |
| `dotenv_path` | Đường dẫn được truyền tường minh; chỉ dùng khi environment không có biến tương ứng |

Environment đã cấp được ưu tiên. Nếu `OPENAI_API_KEY` có mặt nhưng rỗng/sai định dạng, loader dừng; không fallback sang key khác trong `.env`. Không có cơ chế tự tìm `.env` ở thư mục cha hoặc tự export key toàn hệ thống.

Parser `.env` là tập con có chủ đích: UTF-8 hoặc UTF-8 BOM, newline LF/CRLF, dòng trống/comment và một assignment `OPENAI_API_KEY=...`, có thể bọc một cặp quote. Không nhận duplicate, `export`, biến khác, interpolation, shell command, inline comment hoặc escape phức tạp. Token chỉ nhận chữ/số ASCII, `_`, `-` và có giới hạn kích thước. Đây là kiểm format cục bộ, không xác nhận key có hợp lệ hoặc có quyền gọi API.

## Phạm vi sử dụng và đóng scope

`CredentialLease` có các thao tác:

- `environment(base)`: tạo mapping cho đúng child process, chỉ giữ các biến công khai trong allowlist rồi thêm credential. Không tự kế thừa các secret khác.
- `sdk_key()`: trả giá trị cho một SDK sink tường minh sau gate. Hiện chưa có client factory/agent binding thực gọi phương thức này.
- `metadata()`: chỉ tên biến, source enum, target và trạng thái scope/auth; không có key, chiều dài hoặc fingerprint.
- `sanitize(payload)`: loại dữ liệu nhạy cảm trong diagnostic trước khi ghi ra ngoài.

Khi context thoát, lease đóng và các lần truy cập tiếp theo bị từ chối; lỗi trong thân context cũng đóng lease. Python không bảo đảm xóa mọi bản sao string khỏi bộ nhớ. Mapping/lease không thu hồi được giá trị mà caller đã chủ động copy hoặc credential trong một process con đang chạy; quản lý lifecycle của process thuộc binding/runtime sau này.

Gate callback là hợp đồng phần mềm của caller, không phải dịch vụ cấp quyền hoặc sandbox chống code Python tùy ý. Không dùng gate stub của test để mở model run. Trước request thật vẫn cần gate config/review/runtime/budget và provider binding đã kiểm.

## Diagnostic và redaction

Lease/environment mapping có repr che giá trị và không serialize trực tiếp thành JSON. `sanitize()` xử lý field credential/header, Bearer, token dạng key, query parameter nhạy cảm và giá trị secret được cấp tường minh. Object không biết được bỏ qua thay vì gọi repr tùy ý.

`sanitized_error()` chỉ xuất mã lỗi cố định, không lấy message/body/header/traceback locals của exception SDK. Redaction là lớp hỗ trợ; không phải lý do bật debug dump environment, SDK object hoặc credential string. Khi phải scrub giá trị đã nạp, thực hiện trong scope; không giữ key trong một bộ lọc log toàn cục.

## Check metadata và source artifact

Từ root repo, lệnh sau chỉ kiểm metadata, không đọc `.env` hoặc gọi API:

```powershell
python scripts/credential_status.py --output reports/my-credential-metadata.json
```

Dùng output mới. File có mặt không chứng minh giá trị còn hợp lệ; report luôn ghi auth unverified/model dispatch false. `.env.example` chỉ có placeholder rỗng, còn key thật giữ trong `.env` được Git ignore.

`credential_artifacts.py` kiểm member path trước khi hash/copy: root `.env` không thuộc source allowlist; private dotenv nằm trong scripts/configs/tasks/prompts, path ngoài repo, symlink và tên đường dẫn không portable bị từ chối. `.env.example` nếu được đóng gói phải chỉ có comment/assignment rỗng.

Policy này bảo vệ những đường đóng gói đã kiểm, không phải bộ DLP tìm mọi dạng secret bị hard-code hoặc biến đổi trong bất kỳ file nào. Không đưa `.env` vào một lệnh archive toàn workspace khác ngoài allowlist.

## Chạy kiểm định

Trong WSL tại root repo:

```bash
bash scripts/validate-stage8.sh reports/my-new-credential-tests.json
```

Script chuẩn bị Python 3.12.16 nếu cần, áp source policy trước khi gọi native Linux test harness và từ chối ghi đè report. Source snapshot không chứa `.env` thật. Các test credential dùng token giả/mapping/temp file riêng; child process test chỉ trả cờ boolean, không in credential.

Kết quả đã có: [150 test Linux](../reports/stage8-unit-tests.json), [metadata cục bộ](../reports/stage8-credential-status.json), [báo cáo kiểm định](../reports/credential-loader-validation.md). Việc nối SDK/agent, lựa chọn model, budget tiền thực và runtime vẫn chờ đầu vào theo [readiness](../reports/stage8-readiness.md).
