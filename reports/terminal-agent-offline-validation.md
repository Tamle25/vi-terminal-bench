# Kiểm định agent terminal và accounting — giai đoạn 10

Ngày 13/11/2026. Đã kiểm implementation offline; **chưa gọi model, chưa chạy container integration** trong giai đoạn này.

| Kiểm tra | Kết quả / phạm vi |
|---|---|
| Bộ kiểm thử Linux cuối | **203/203 đạt**, 0 failure/error/skip; 39 test mới |
| Runtime test | Python 3.12.16; native Linux byte-verified copy, 204 public input |
| Vòng lặp tool | History/reasoning/tool output/call ID; UTF-8 NFC/NFD; bound request/context; gate và config drift |
| USD ledger | Atomic claim, cap pool/run, nhiều controller, exposure import chống trùng, unknown giữ hold, invoice revision không cộng trùng |
| Chống replay | Trial/request/tool claim bền vững; crash sau submit/tool không tự chạy lại |
| Backend/artifact | Docker command đi qua argv; kiểm policy thực bằng inspect fixture; capture có bound, không truyền host API env; tar từ chối link/traversal/oversize |
| Verifier | Reward 0 hợp lệ, verifier error khác reward 0, fixture không trở thành benchmark |
| Controller | Compute hold trước create, owner token sang loop, thứ tự start/collect/verifier/cleanup, draft bị từ chối trước Docker/key |
| Worker và storage | Credential qua stdin, deadline/kill ở parent, không argv/env; persistent ledger không reset claim khi đổi output folder |
| Compute revision | Estimate không release reserve; latest invoice revision thay charge, giữ raw estimate |
| Integration Linux | Hai fixture EN/VI, bốn response giả, hai probe Python cố định, transfer dữ liệu và grader B001 thật |
| Kết quả grader fixture | 0 và 0 theo dữ liệu cố ý không giải task; không phải điểm model |
| Restore | Backup DB trong archive khôi phục được; bốn request/two tool claim/hai invoice revision fixture được kiểm |
| Docker/model/key thật | Không dùng trong integration/test; số request provider mới = 0 |

Evidence cuối: [unit report](stage10-unit-tests-final.json), [integration report](stage10-offline-validation-final.json) và [fixture archive](stage10-offline-evidence-final.tar.gz). Source hash của bản kiểm nằm trong hai JSON; credential policy loại `.env` trước hash/copy. Fixture USD chỉ là unit tiền có origin `offline-fixture`, không phải charge thật hoặc permission dùng USD.

Checkpoint 197 test trước khi bổ sung controller/worker/schema 1.1 được giữ trong [unit report ban đầu](stage10-unit-tests.json), [source snapshot tương ứng](stage10-initial-source.zip) và [integration ban đầu](stage10-offline-validation.json); không dùng hash bản cũ để kiểm source cuối đã thay đổi hợp lệ.

Integration dùng đúng instruction EN/VI và generator của B001. Backend fixture chỉ chấp nhận token `fixture-probe`, chạy một Python probe do validator cố định, viết hai output JSONL rỗng rồi transfer và gọi grader dữ liệu. Không thực thi shell text do model trả trên host, không dùng oracle và không gọi đây là kiểm container/isolation. Grader từ chối dữ liệu rỗng như dự kiến.

Chẩn đoán lại [WSL/Docker](stage10-runtime-diagnosis-final.json): không có `/var/run/docker.sock`, CLI báo Docker Desktop WSL integration chưa hoạt động. Không restart/prune/switch endpoint hoặc bật relay. Không có attestation mới cho smoke. Cần kiểm create/start/exec/pause/copy/verifier/cleanup bằng container thật sau khi người vận hành khôi phục runtime.

Giới hạn còn lại: controller/worker/compute workflow mới được kiểm offline, chưa nghiệm thu bằng backend/container/provider thật và quote thực. Chưa có provider cancel/lookup hoặc resume partial. Không dùng kết quả unit/fixture để ghi các năng lực thực đó đã đạt.
