# Báo cáo triển khai và kiểm định ban đầu

Ngày báo cáo: 12/11/2026, giờ Việt Nam. Phạm vi M1/S1–S6 của kế hoạch; đây là kiểm định kỹ thuật, không phải kết quả đánh giá model.

## Kết quả

| Hạng mục | Bằng chứng | Kết quả |
|---|---|---|
| Đặc tả, giao thức, quyết định | docs/benchmark-spec.md, evaluation-protocol.md, decisions.md | Đã tạo |
| Task Harbor | b001-vn-invoice, b002-unicode-files | Cấu trúc và schema Harbor 0.25.0 hợp lệ |
| Instruction | EN/VI của cả hai task | Có bản mặc định VI và script materialize giữ payload |
| Verifier controls trong Linux | [controls.json](controls.json) | 45/45 khớp kỳ vọng: 8 positive, 37 negative |
| Oracle qua Harbor | [harbor-oracle-linux.json](harbor-oracle-linux.json) | 6/6 reward 1, mỗi task 3/3, không exception |
| No-op qua Harbor | [harbor-nop-linux.json](harbor-nop-linux.json) | 2/2 reward 0, không exception |
| Verifier riêng | verifier_environment_mode trong từng trial | Cả 8 trial cuối dùng separate verifier |
| Image agent mới | [agent-images.json](agent-images.json) | Cả 2 image không chứa /tests, /solution hoặc expected trong /app |
| Cách ly mạng/tài nguyên | [isolation.json](isolation.json) | Các container quan sát được đều network none; đây là snapshot, không phải audit toàn diện |
| Công cụ tính điểm | scripts/tests/test_aggregate_results.py | 9/9 unit test đạt |
| Provenance môi trường | [environment.json](environment.json), configs/development.json, uv.lock | Đã ghi phiên bản, dependency và image digest |

Positive controls gồm oracle ba lượt/task và một cách giải khác/task. Negative controls gồm no-op và các lỗi dữ liệu: bỏ dấu/NFD, BOM, ngày-tháng, số tiền/kiểu boolean, thiếu dòng/file, nguồn bị thay đổi, overwrite, hash sai, sai thứ tự, symlink, JSON lồng sâu và file quá lớn. Các control này không chứng minh không còn mọi kiểu reward hack.

Expected hóa đơn là dữ liệu tĩnh tách khỏi oracle. Có cách giải development khác dùng xử lý lịch/nhóm số riêng; JSON đảo key, ASCII escape, CRLF và không newline cuối vẫn được chấp nhận. Chưa có reviewer con người độc lập; không coi kiểm tra của cùng phiên triển khai là thay thế review đó.

## Hai lỗi hạ tầng đã phát hiện và xử lý

1. **Policy tắt mạng động không hoạt động trên kernel/backend hiện tại.** Job `jobs/m1-oracle-vi` bị từ chối trước khi chạy trial; không tính đây là model fail. Cấu hình cuối dùng Docker Compose `network_mode: none` cho cả environment và tests, không bật mạng để vượt lỗi. TOML để policy Harbor public để không kích hoạt backend egress động; ràng buộc offline do Compose thực thi.
2. **Filesystem Windows làm mất phân biệt tên file.** Trong job `jobs/m1-oracle-vi-static-network`, B001 pass 3/3 nhưng B002 fail 3/3 với `Source names changed/missing`. Artifact đi qua ổ D không giữ được cặp tên khác hoa/thường. Chuyển jobs và artifact sang filesystem Linux trong WSL giải quyết vấn đề: job `m1-oracle-linux` pass 6/6. Không loại bỏ fixture khó hoặc nới verifier. Wrapper hiện chặn jobs-dir dưới `/mnt` để tránh tái diễn.

Các báo cáo [harbor-oracle.json](harbor-oracle.json) và [harbor-nop.json](harbor-nop.json) giữ kết quả trước sửa đường dẫn để điều tra; **không phải kết quả nghiệm thu cuối**. Nop trước sửa có thể fail sớm ở kiểm tra nguồn Unicode; kết quả nop cuối trên Linux mới xác nhận thiếu output đúng điều kiện.

## Artifact và cách tái lập

- Raw jobs cuối nằm trong WSL: `/tmp/vi-terminal-bench-runtime/jobs/m1-oracle-linux` và `m1-nop-linux`.
- JSON tổng hợp nhỏ ở reports; không chép cây raw artifact có tên nhạy Unicode sang Windows.
- Đã sao lưu hai raw job cuối vào `jobs/m1-linux-validation.tar.gz` trong workspace; thư mục jobs bị Git ignore. Archive giữ nguyên tên file khi chuyển qua Windows, cần giải nén trên filesystem Linux.
- [task-snapshot.json](task-snapshot.json) lưu manifest và hash payload/instruction của hai dataset EN/VI đã materialize; hash payload ngoài instruction giống nhau.
- Vùng /tmp có thể bị dọn; sao lưu bằng tar từ Linux trước khi chép archive sang Windows.
- [Hướng dẫn](../docs/development.md) có lệnh setup, schema validation, controls, oracle và nop.
- Task/runtime Python 3.12.12, Unicode 15.0.0; harness Python 3.12.16; Harbor 0.25.0; Docker Engine 28.1.1.
- Image digest được cố định trong cả bốn Dockerfile. Dependency harness trong uv.lock; interpreter harness khóa qua .python-version và setup script.
- Git đã khởi tạo; thay đổi hiện nằm trong workspace, chưa tạo commit hoặc phát hành.

## Những phần chưa hoàn thành

- Chưa có review kỹ sư Việt Nam độc lập hoặc đo thời gian chuyên gia.
- Chưa có snapshot/cấu hình tiếng Anh từ Eval, chưa nhập/dịch task A.
- Chưa chọn model/agent/ngân sách; không gọi API model, không có điểm model hoặc chi phí inference.
- Chưa có bốn task B còn lại của pilot, chưa chạy 216 trial pilot.
- Công cụ tổng hợp nhận JSONL chuẩn hóa; chưa có adapter tổng quát từ output model/Harbor, chưa tính CI bootstrap.
- Chưa chọn giấy phép phát hành hoặc split test kín. Hai task hiện là development công khai trong workspace.

Mốc tiếp theo là review hai task và thực hiện backlog pilot trong [pilot-backlog.md](pilot-backlog.md). Không đánh dấu hoàn tất toàn bộ kế hoạch giai đoạn đầu hoặc v1.0 từ kết quả M1.
