# Kết quả bản benchmark B nhỏ — development

Ngày 13/11/2026. Run `stage11-development-001` đã hoàn tất **36/36 trial hợp lệ**, gồm sáu task B × EN/VI × ba repeat × một cấu hình. **35 pass, một fail do lời giải agent; không còn trial thiếu hoặc lỗi hạ tầng chưa giải quyết trong coverage cuối.**

Model `gpt-5.4-mini-2026-03-17`, reasoning none, host terminal agent; giới hạn sáu request/trial và 2.048 output token/request. Dataset/task version 0.1.0, snapshot `490323ee9077ad81f00c2468a69ecd45884cba7caafb0a1dca1f1507b8679288`. Kết quả **nội bộ, chưa review độc lập**, tác giả task vẫn `Codex-assisted`.

| Nhóm / task | EN | VI |
|---|---:|---:|
| Hóa đơn, số/ngày — B001 | 3/3 | 3/3 |
| Unicode/tên file — B002 | 2/3 | 3/3 |
| Windows-1258 — B003 | 3/3 | 3/3 |
| Tìm không dấu — B004 | 3/3 | 3/3 |
| Collation tiếng Việt — B005 | 3/3 | 3/3 |
| CSV/BOM/CRLF — B006 | 3/3 | 3/3 |
| Tổng | **17/18 — 94,44%** | **18/18 — 100%** |

Macro qua task: EN **94,44%**, VI **100%**, delta VI−EN **+5,56 điểm phần trăm**. Tỷ lệ pass gộp là **35/36 = 97,22%**. Mỗi nhóm hiện có một task nên điểm nhóm bằng điểm task. Không có CI theo phương pháp đã chọn vì chỉ một family/nhóm; kết quả nhỏ này không đủ kết luận ngôn ngữ nào tốt hơn nói chung hoặc xếp hạng model.

## Lỗi agent được giữ nguyên

`b002-unicode-files--en--r1--mini` thiếu artifact đích mà grader yêu cầu: `output/files/0001--Báo cáo.txt`. Grader offline chạy lại trên **cùng artifact** vẫn cho reward 0. Không sửa output, đổi prompt hoặc chạy lại model để lấy điểm cao hơn; hai repeat EN sau là các trial độc lập đã lập trước. Xem [chẩn đoán](stage11-failure-analysis.json).

## Chi phí và coverage

| Khoản | Giá trị |
|---|---:|
| Batch 36 trial | 76 response provider; token estimate bảo thủ **0,11385825 USD** |
| Hai run smoke riêng, bốn trial | 9 response provider; token estimate bảo thủ **0,02106375 USD** |
| Tổng giai đoạn 11 | 85 response provider; estimate bảo thủ **0,134922 USD** |
| Cộng connectivity giai đoạn 9 | Estimate bảo thủ cộng dồn **0,1349925 USD** |
| Cộng dồn theo giá có discount cached input | **0,1340421 USD**, chưa invoice |
| Trần pool | **2 USD** |

Tính từ usage trả về và [giá OpenAI](https://developers.openai.com/api/docs/models/gpt-5.4-mini) đã kiểm 13/11/2026. Estimate bảo thủ tính input như uncached; estimate theo cached input được lưu riêng. Các số này chưa phải hóa đơn. Compute local ghi `not_metered`, không tự quy thành 0 USD. Hold connectivity 0,01 USD và correction margin 0,10 USD vẫn giữ, không cộng thành hai khoản phí mới. [Usage/ledger](stage11-usage-and-budget.json) có chi tiết từng request.

## Runtime và recovery

Runtime là relay `desktop-shared-relay-v2` tới Docker Desktop, workload chạy user thường, agent/verifier không mạng và không nhận key/socket/đáp án. Controller được ghim CPU 0 khi tiếp tục sau lỗi thời gian attestation; quota agent vẫn 1 CPU. Thời gian controller gồm setup/tool/verifier, không được diễn giải thành latency thuần của model.

Sau 25 trial hợp lệ, một gate từ chối **trước HTTP worker**. Intent đó được sao lưu, lưu raw receipt/trace và audit cancellation với phí API 0 theo bằng chứng chưa dispatch; không release một timeout hoặc HTTP error chưa rõ phí. 25 kết quả cũ giữ nguyên, kể cả reward 0, rồi tiếp tục 11 điều kiện chưa gửi. [Audit](stage11-pre-dispatch-cancellation.json) và checkpoint có trong archive. Một intent bị chặn không phải response provider hoặc model retry.

## Tái lập

- [Quickstart và CLI](../docs/development-benchmark-quickstart.md).
- [Summary JSON](development-benchmark-summary.json), [CSV](development-benchmark-trials.csv), [normalized JSONL](development-benchmark-trials.jsonl) và [report sinh bằng CLI](development-benchmark-results.generated.md).
- [Manifest 36 trial](stage11-batch-plan.json), [source snapshot lúc freeze](stage11-batch-source.zip), [kiểm container](stage11-container-validation.json).
- [Proof dựng lại report/resume](stage11-reproduction-proof.json): JSONL/CSV/Markdown khớp byte; completed resume không tạo request mới.
- [Archive Linux](stage11-native-evidence.tar.gz) và [proof restore](stage11-native-archive-proof.json): 604 file khôi phục đúng hash, giữ tên Unicode/case-distinct và ledger.

Review vẫn 0/6 và giấy phép phát hành task chưa chốt. Đây là **bản nhỏ development dùng được**, chưa phải bộ A+B hoặc bản phát hành benchmark đã kiểm độc lập.
