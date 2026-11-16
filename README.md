# Vietnamese Locale-aware Terminal Benchmark

Bản benchmark development v0.1 đánh giá AI agent làm việc trong terminal với yêu cầu và dữ liệu tiếng Việt. Bản nhỏ đã chạy thật sáu task B × EN/VI × ba repeat: **36/36 trial hợp lệ, 35 pass**. Chưa review độc lập hoặc phát hành dataset chính thức.

Dashboard cục bộ: chạy `python dashboard/server.py`, rồi mở **http://127.0.0.1:8765** để xem kết quả, chạy smoke/batch và theo dõi tiến độ. Xem [hướng dẫn dashboard](dashboard/README.md). Các nút chạy model dùng chung pool tối đa 2 USD của CLI.

- [Đặc tả](docs/benchmark-spec.md): hai phần ngôn ngữ instruction và xử lý dữ liệu Việt Nam.
- [Giao thức](docs/evaluation-protocol.md): repeat, retry, reward và phép tính điểm.
- [Hướng dẫn chạy](docs/development.md): WSL, Docker, Harbor và kiểm định.
- [Báo cáo M1](reports/initial-validation.md).
- [Kiểm định native-six](reports/native-six-validation.md) và [điều kiện pilot](reports/pilot-readiness.md).
- [Giai đoạn 3: readiness trước đó](reports/stage3-readiness.md), [runtime](reports/runtime-diagnosis.md) và [dry-run model](reports/model-pilot-dry-run.md).
- [Giai đoạn 4: readiness trước đó](reports/stage4-readiness.md), [kiểm định runner offline](reports/pilot-runner-offline-validation.md) và [hướng dẫn runner](docs/pilot-runner.md).
- [Giai đoạn 5: readiness trước đó](reports/stage5-readiness.md), [kiểm định executor](reports/model-executor-offline-validation.md) và [hướng dẫn CLI](docs/model-executor.md).
- [Giai đoạn 6: readiness trước đó](reports/stage6-readiness.md), [kiểm định billing](reports/shared-billing-offline-validation.md) và [reconciliation runbook](docs/reconciliation-runbook.md).
- [Giai đoạn 7: readiness trước đó](reports/stage7-readiness.md) và [gói quyết định để chạy model](reports/stage7-decision-package.md).
- [Giai đoạn 8: readiness trước đó](reports/stage8-readiness.md), [kiểm định credential loader](reports/credential-loader-validation.md) và [hướng dẫn](docs/credential-loading.md).
- [Giai đoạn 9: readiness trước đó](reports/stage9-readiness.md), [kết nối OpenAI thực](reports/provider-connectivity.md), [run spec](reports/stage9-run-spec.md) và [hướng dẫn client](docs/provider-connectivity.md).
- [Giai đoạn 10: readiness trước đó](reports/stage10-readiness.md), [thiết kế agent terminal](docs/terminal-agent-design.md), [kiểm định offline](reports/terminal-agent-offline-validation.md) và [gói review B001](reports/reviews/stage10-b001-opening.zip).
- [Giai đoạn 11: readiness hiện tại](reports/stage11-readiness.md), [kết quả 36 trial](reports/development-benchmark-results.md), [quickstart/CLI](docs/development-benchmark-quickstart.md) và [protocol nội bộ](docs/development-benchmark-protocol.md).
- [Kế hoạch giai đoạn đầu](Plan/plan-giai-doan-dau.md).
- [Kế hoạch giai đoạn 2](Plan/plan-giai-doan-2.md).
- [Kế hoạch giai đoạn 4](Plan/plan-giai-doan-4.md).
- [Kế hoạch giai đoạn 5](Plan/plan-giai-doan-5.md).
- [Kế hoạch giai đoạn 6](Plan/plan-giai-doan-6.md).
- [Kế hoạch giai đoạn 7](Plan/plan-giai-doan-7.md).
- [Kế hoạch giai đoạn 8](Plan/plan-giai-doan-8.md).
- [Kế hoạch giai đoạn 9](Plan/plan-giai-doan-9.md).
- [Kế hoạch giai đoạn 10](Plan/plan-giai-doan-10.md).
- [Kế hoạch giai đoạn 11](Plan/plan-giai-doan-11.md).
- [Checklist dữ liệu từ Eval](docs/eval-input-checklist.md).

Đã có sáu task: hóa đơn VND/ngày tháng, file Unicode NFC/NFD, chuyển Windows-1258, tìm không dấu, collation tiếng Việt và xuất CSV. Mỗi task có EN/VI, oracle, alternative và verifier artifact riêng. Kiểm định: 18/18 oracle pass, 6/6 nop nhận điểm 0, 125 controls và 27 test đạt; chưa có điểm model.

Sau giai đoạn 4, bộ test công cụ đã mở rộng và đạt 70/70 trên Linux/WSL. Runner mô phỏng hoàn tất 72 trial, 74 lượt fake dispatch gồm hai retry, kiểm tra dừng/resume và khôi phục ledger; không gọi API hoặc tính điểm model. Review độc lập vẫn 0/6, model runtime và adapter thật chưa được chọn/kiểm định.

Giai đoạn 5 bổ sung scope smoke/pilot và đường executor offline, đạt 102/102 test Linux. Kiểm định CLI riêng có hai trial fixture, ba attempt/năm request, gate trước request và accounting/resume đầy đủ; chưa có provider binding hoặc kết quả model thật.

Giai đoạn 6 bổ sung ledger ngân sách chung giữa run/scope và CLI nhập receipt có revision, đạt 126/126 test Linux. Integration hai request fixture kiểm crash/replay, correction overlay và restore năm DB; chỉ SIM_USD, chưa có chi phí hoặc model/API call thật.

Giai đoạn 7 đã kiểm inventory và chuẩn bị gói quyết định; chưa có reviewer/model/budget/runtime mới. G7.1 vẫn thiếu đầu vào, chưa chạy model hoặc thêm simulation. Dùng gói quyết định để tiếp tục U1–U4 khi có lựa chọn thực.

Sau giai đoạn 7, credential OpenAI được lưu cục bộ trong `.env` được Git bỏ qua. Giai đoạn 8 đã kiểm loader theo process, redaction và source-artifact policy, đạt 150/150 test Linux. Key thật không được đưa vào test snapshot hoặc dùng để gọi API; agent/model/budget và provider binding thực vẫn chưa chốt/triển khai.

```bash
# Trong WSL, tại root dự án; Docker Linux phải hoạt động.
bash scripts/setup-wsl.sh
/tmp/vi-terminal-bench-runtime/venv/bin/python scripts/validate_dataset.py --harbor
# Dùng run ID mới; manifest được lập trước khi chạy.
bash scripts/run_native_validation.sh oracle my-new-validation
```

Giai đoạn 9 đã chốt model kết nối `gpt-5.4-mini-2026-03-17` và trần kiểm tra 2 USD theo ủy quyền của người dùng. Một request OpenAI Responses thực nhận HTTP 200/completed, dùng 22 input và 12 output token; chi phí theo usage/giá công bố ước tính 0,0000705 USD, chưa đối soát invoice. Bộ kiểm thử đạt 164/164 trên Linux. Đây là bằng chứng kết nối, chưa có terminal benchmark smoke hoặc điểm model; review độc lập vẫn 0/6, agent/runtime và hai cấu hình/budget pilot còn mở.

Giai đoạn 10 bổ sung host tool loop/controller, worker HTTP có deadline, Docker/verifier/artifact primitive và ledger USD nhiều request/compute revision; 203/203 test Linux đạt cùng hai integration fixture EN/VI. CLI mặc định preview, draft execute bị từ chối; không gọi thêm API. Docker/WSL hiện fail, review 0/6 và ngân sách/compute smoke chưa chốt; gói review pending đã có. Backend thực chưa nghiệm thu, chưa có điểm benchmark model.

Giai đoạn 11 đạt bản nhỏ dùng được: backend sáu task đã kiểm bằng 6 oracle/6 no-op trên Docker thật; model `gpt-5.4-mini-2026-03-17` chạy 36 trial, EN 94,44%, VI 100%, delta +5,56 điểm phần trăm. Một lời giải sai được giữ nguyên. Token estimate bảo thủ cộng dồn cả smoke/connectivity khoảng 0,135 USD trong trần 2 USD; chưa invoice, local compute not-metered. Hồi quy cuối 223/223 test Linux đạt; report tái tạo và completed resume không gửi request mới; archive restore kiểm 604 file. Runtime dùng shared relay v2 và pin controller CPU 0; review vẫn 0/6 pending, kết quả chỉ development/internal.

Jobs/artifact benchmark lưu trên filesystem Linux. Dùng [quickstart](docs/development-benchmark-quickstart.md) để gọi một CLI plan/run/resume/report qua runtime đã kiểm. Không chép cây raw có tên Unicode/case-distinct sang ổ Windows; dùng archive Linux. Chưa có baseline A hoặc reviewer độc lập. Nguồn và trạng thái giấy phép trong [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
