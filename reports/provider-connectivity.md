# Kết quả kết nối provider — giai đoạn 9

Ngày 13/11/2026, run `stage9-openai-connectivity-001` đã gửi **một request thực** tới OpenAI Responses API và nhận **HTTP 200 / completed**.

| Bằng chứng | Quan sát |
|---|---|
| Model yêu cầu / trả về | `gpt-5.4-mini-2026-03-17` / khớp |
| Provider request ID | `req_629b0aa56cdc4bf39ea64b6b584a8982` |
| Response ID | `resp_01dea993871f169c016af66e0904b487d29e77066d0817e3ab` |
| Nội dung trả về | Kết nối tiếng Việt thành công. |
| Usage | 22 input token; 0 cached; 12 output token; 0 reasoning; tổng 34 |
| Service tier | `default` |
| Chi phí token ước tính | **0,0000705 USD** |
| Trần được phép | 2,00 USD cho đợt kiểm tra |
| Reservation còn giữ | 0,01 USD, đến khi đối soát hóa đơn |
| Retry / request phụ / tool | 0 / 0 / 0 |
| Benchmark trial / điểm | 0 / chưa có |

Công thức: `(22 × 0,75 + 12 × 4,50) / 1.000.000 = 0,0000705 USD`, theo [giá OpenAI Docs](https://developers.openai.com/api/docs/models/gpt-5.4-mini) đã kiểm ngày 13/11/2026. Đây là tính toán từ usage trả về và đơn giá standard, chưa có invoice/account billing receipt. Không cộng reservation và estimate thành hai khoản phí; chưa release reservation.

Key đã được provider chấp nhận cho request/model này. Kết quả không xác minh danh tính chủ tài khoản/project ID, số dư còn lại hoặc quota cho pilot. Không có call list-models/auth phụ và không fallback model. Key không được in ra hoặc đưa vào snapshot Linux, source archive, receipt hay terminal argv.

Artifact máy đọc: [receipt](provider-connectivity-stage9.json), [manifest](stage9-frozen-inputs.json), [run spec](stage9-run-spec.md), [kiểm thử Linux](stage9-unit-tests.json). Receipt chứa model, usage, provider ID và response đã redaction; ledger local giữ claim đã hoàn tất nên không thể gửi lại run bằng cùng runner.

Đây là kiểm kết nối provider, **chưa phải terminal agent smoke hoặc điểm benchmark**. Review độc lập vẫn 0/6; terminal tools/isolation/runtime chưa được attestation cho run model. Không dùng kết quả này để ghi pass các mốc smoke/pilot.
