# Kiểm định shared billing và reconciliation offline

Kết quả bản cuối ngày 12/11/2026: **126/126 test Linux đạt**, 0 failure/error/skip. Integration có **hai request fixture và bốn receipt revision**, không gọi model/API thật. Nguồn và 182 input file được đối chiếu byte/hash trên bản sao filesystem Linux; Python 3.12.16.

## Hành vi đã kiểm

| Nhóm | Kết quả |
|---|---|
| Ngân sách chung | Reservation kiểm đồng thời cap pool/run; hai run tranh gần cap chỉ một được nhận |
| Pending/uncertain | Giữ exposure; chặn scope khác trong cùng pool; pool độc lập và external hold xử lý riêng |
| Tiền và trạng thái | SIM_USD khác USD; actual 0 khác null; known cost không được xóa bằng null revision |
| Outbox | Crash sau global reserve/claim/receipt không làm mất reservation hoặc tự resend |
| Receipt import | Raw hash/identity/chain phải khớp; duplicate không cộng lại phí; bảo toàn task result và provider request ID |
| Binding | Sai DB dù cùng reference ID nhưng khác pool spec/run manifest bị từ chối |
| Correction | Ledger/overlay ghi phí mới; raw task đã settle giữ nguyên, có delta đối chiếu |
| CLI | Status read-only không đổi rows/events; import crash sau global commit rồi replay sync local thành công |
| Recovery | Receipt đầy đủ có thể settle; partial thiếu checkpoint tiếp tục uncertain; reconcile không vượt runtime gate |
| Backup | Năm DB của integration đóng trước archive, được mở lại kiểm sau restore |

## Integration hai scope fixture

Pool dùng chung có cap **1.500 inference / 200 compute micro-unit SIM_USD**. Đây là số giả để kiểm logic, không phải budget API đề xuất.

1. Request smoke fixture trả kết quả nhưng cost null; fault injection dừng sau global receipt, trước local sync. Pilot fixture bị chặn, không tạo request provider.
2. Receipt v2 xác nhận 800/80. CLI bị ngắt sau global commit; reimport cùng receipt hoàn tất sync mà không charge hai lần hoặc gửi lại request. Task result được bảo toàn.
3. Với 800/80 đã dùng, pool chưa đủ reservation 1.000/100 cho request pilot; gate tiếp tục chặn.
4. Receipt v3 điều chỉnh phí smoke thành 400/80, có source/reason/chain. Raw task lúc settle vẫn 800/80; overlay ghi 400/80.
5. Request pilot fixture được nhận khi pool đủ tiền, charge 1.000/100. Tổng authoritative là **1.400/180**, còn 100/20; tổng legacy task accounting là 1.800/180 và delta billing là −400/0.

Chỉ chọn một request trong mỗi fixture scope để kiểm khoảng trống accounting. Đây không phải smoke model thật hoặc pilot 72 trial hoàn chỉnh. Reward giả không được dùng như điểm benchmark.

## Bằng chứng bản cuối

- [126 test Linux và input hashes](stage6-final-unit-tests.json).
- [Integration summary](stage6-final-offline-summary.json).
- [Archive global/local/provider DB, receipts, outbox và source](../jobs/stage6-final-shared-billing.tar.gz).
- [Hợp đồng shared billing](../docs/shared-billing-ledger.md), [runbook reconciliation](../docs/reconciliation-runbook.md).

SHA-256 archive: `9524d980078ec37be87e691378bae89aabc5fce9a733e89fcc43635d8831126a`.

Các output mang prefix `stage6-final` là bằng chứng của source cuối cùng. Report/archive prefix `stage6` trước đó được giữ riêng; bản cuối bổ sung kiểm binding nhầm ledger và kiểm known charge không bị xóa bằng null. Không ghi đè kết quả cũ.

## Giới hạn

Ledger và receipt chỉ thuộc fixture SIM_USD. Chưa có provider/account/budget thật, chưa xác thực giá/usage/SDK retry, không có remote lookup/cancel hoặc checkpoint recovery thực. File có hash khớp chứng minh nhất quán dữ liệu, không xác thực rằng provider thật phát hành receipt.

Overlay billing là nguồn đối chiếu phí sau adjustment; normalized task snapshot cũ không tự trở thành hóa đơn mới. Partial agent state vẫn cần capability cụ thể và bằng chứng trước khi có thể tiếp tục. Restore chứng minh dữ liệu bền vững, không cấp quyền dispatch từ input đã di chuyển.

Task/prompt, source đã đóng băng của các giai đoạn trước và report/archive lịch sử được giữ nguyên. Review độc lập vẫn 0/6; phần A, model smoke/pilot và phát hành chưa thực hiện. Xem [readiness giai đoạn 6](stage6-readiness.md).
