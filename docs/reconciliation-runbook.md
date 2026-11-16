# Quan sát và reconcile billing fixture

Các lệnh trong `scripts/reconcile_billing.py` chỉ đọc hoặc cập nhật ledger fixture cục bộ, **không gọi provider/model**. Chúng không phải bằng chứng xác thực billing từ provider thật. Mọi envelope phải có `origin=offline-fixture`, đúng request/run/pool và raw evidence khớp hash.

## 1. Quan sát trước khi cập nhật

Trong WSL, tại root repo, dùng Python 3.12.16 đã chuẩn bị. Có thể xem archive final mà không chạm state gốc:

```bash
PY=/tmp/vi-terminal-bench-runtime/offline-tests/bin/python
RESTORED=$(mktemp -d /tmp/vi-stage6-inspect-XXXXXX)
tar -xzf jobs/stage6-final-shared-billing.tar.gz -C "$RESTORED"
"$PY" scripts/inspect_billing_state.py \
  --ledger "$RESTORED/state/shared.sqlite3" \
  --local-state "$RESTORED/state/fixture-smoke/state/ledger.sqlite3" \
  --output "$RESTORED/status.json"
```

Status mở DB read-only, không tạo ledger nếu path thiếu, không ghi event hoặc thay row. Report thể hiện pool/run, request phase, reservation/actual, holds, receipt revisions, local outbox/overlay, owner/lease của execution local và thời điểm quan sát. `reconcile_billing.py status` vẫn cung cấp view cơ bản. Các snapshot của hai DB không phải một transaction nguyên tử; khi controller còn hoạt động, đọc theo thời điểm tương ứng và kiểm lại trước thao tác cập nhật.

## 2. Chuẩn bị receipt evidence

Envelope schema `vi-billing-receipt/0.1` gồm:

```text
schema, origin, identity, revision, previous_sha256,
reason, source, provider_request_id, result, raw_sha256
```

`identity` gồm pool/run/request/trial/attempt/slot và bound đã đăng ký. Raw JSON chứa request ID, provider request ID và result. Result gồm `status`, `reward`, `inference_micros`, `compute_micros` theo hợp đồng executor. Giữ nguyên raw bytes dùng để tính SHA-256; chỉnh whitespace rồi dùng hash cũ sẽ bị từ chối.

Revision đầu là 1, `previous_sha256=null`; các revision sau phải nối đúng chain. Reimport revision đã có chỉ được coi là idempotent nếu nội dung/raw evidence giống hệt. Known task status/reward và provider request ID không được đổi trong billing correction. Thay phí đã biết cần reason `provider-billing-adjustment` và amount mới cụ thể, không phải null.

File có hash khớp chỉ chứng minh nhất quán dữ liệu. Khi triển khai provider thật phải xác minh nguồn receipt qua adapter/capability tương ứng; việc tự điền JSON không tạo bằng chứng provider đã nhận/chưa nhận hay đã charge/chưa charge.

## 3. Import và replay sau crash

Archive final đã có receipt v2/v3 để kiểm tra replay. Lệnh sau nhập lại v3 trên bản sao vừa giải nén:

```bash
"$PY" scripts/reconcile_billing.py import-receipt \
  --ledger "$RESTORED/state/shared.sqlite3" \
  --local-state "$RESTORED/state/fixture-smoke/state/ledger.sqlite3" \
  --receipt "$RESTORED/state/receipt-v3.json" \
  --raw-evidence "$RESTORED/state/raw-v3.json" \
  --output "$RESTORED/import-result.json"
```

Đây là reimport fixture đã được settle, không phát sinh request mới. Global receipt không cộng lại phí; local sync sử dụng revision mới nhất. Nếu crash sau global commit nhưng trước local sync, chạy lại cùng receipt để hoàn tất sync. Không sửa revision hoặc tạo request ID mới chỉ để vượt lỗi.

Local recovery kiểm frozen source/binding và metadata pool/run. Chọn nhầm DB có cùng reference ID nhưng khác manifest/caps vẫn bị từ chối. Khi source khác phiên đã đóng băng, cần quy trình migration/review rõ ràng; không bỏ kiểm hash để tiếp tục.

## 4. Xử lý theo trạng thái

| Trạng thái/bằng chứng | Hành động |
|---|---|
| Reserved, global claim chưa diễn ra | Có thể giữ chờ hoặc dùng `cancel-reserved` với đúng request ID |
| Submitted, không có receipt đủ | Giữ exposure; không resend hoặc release chỉ vì timeout/lease hết |
| Receipt đầy đủ, local chưa persist | Import/replay và sync; không gọi lại model |
| Task result đã biết, cost thiếu | Giữ reward; giữ billing uncertainty và reservation |
| Partial request đã xong, agent checkpoint thiếu | Giữ task chưa hoàn tất, không tự chạy lại toàn bộ |
| Có billing correction | Thêm revision có nguồn; overlay phản ánh delta, raw task cũ giữ nguyên |

`cancel-reserved --ledger ... --request-id ...` chỉ chấp nhận global request chưa claim. Nó không tự settle local task hoặc gán reward 0. CLI không có lệnh “force resend”, “clear uncertainty” chung hoặc remote lookup/cancel; các khả năng đó phải được kiểm theo provider khi có binding thực.

Sau reconcile, request mới vẫn phải qua gate hiện tại về review, snapshot/config, runtime còn hạn và budget. Một receipt hợp lệ không thay thế các điều kiện đó.

## 5. Backup, test và tiền thực

Archive khi controller/connection đã đóng, bao gồm shared ledger, hai DB local/provider của mỗi run, outbox, receipts/raw evidence và source provenance. Integration final kiểm năm DB của hai scope fixture. Nếu hệ thống còn đang ghi, cần thiết kế backup nhất quán/outbox recovery; không copy riêng main SQLite file rồi bỏ WAL.

Để kiểm phiên bản code hiện tại bằng một bộ output mới:

```bash
# Prefix mới, chưa có report/archive cùng tên.
bash scripts/validate-stage6.sh my-stage6-check
```

Script giữ một phiên WSL xuyên suốt bootstrap Python, native Linux tests và integration; từ chối ghi đè bằng chứng. Case fixture chỉ kiểm khoảng trống billing/reconciliation, không chạy thêm một bộ 72 trial giả.

Ledger hiện từ chối tiền thực/USD. Model profile, account, nguồn giá, reviewer và runtime thật vẫn cần được cung cấp/kiểm định trước bước T3–T5. Không đổi nhãn SIM_USD sang USD hoặc gỡ guard `--mode model` để đi qua bước này.
