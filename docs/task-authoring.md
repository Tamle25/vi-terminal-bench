# Hướng dẫn viết và review task

## Mẫu task card

ID; family_id; phiên bản; track; năng lực chính/phụ; độ khó dự kiến; thời gian chuyên gia; tình huống; đầu vào; đầu ra; quy tắc locale; trường hợp lỗi; oracle; các mutant; cách giải khác; nguồn/giấy phép; reviewer và trạng thái.

## Cấu trúc

Mỗi task có instruction.md (VI mặc định), task.toml, environment/Dockerfile, solution/solve.sh, solution/solve.py, tests/Dockerfile, tests/test.sh và tests/grader.py. Bản EN/VI trong prompts là nguồn để materialize. Metadata riêng dùng manifest; không đưa field chưa được Harbor hỗ trợ vào cấu hình.

Agent image build từ thư mục environment, chỉ chứa fixture/generator. Verifier image build từ tests, chứa grader/đáp án riêng. Oracle nằm ngoài agent build context. Khai báo artifact đầu ra và nguồn nếu cần kiểm tra bảo toàn. Verifier không import/chạy code submission; JSON chỉ được parse như dữ liệu, từ chối symlink, file không thường, file quá lớn và duplicate JSON keys.

## Checklist review

- [ ] Mọi điều kiện chấm đều có trong instruction hai ngôn ngữ.
- [ ] Encoding, schema, loại dữ liệu, thứ tự và các trường hợp bằng nhau rõ ràng.
- [ ] Fixture có case bình thường, biên và lỗi; expected output được kiểm tra độc lập.
- [ ] Oracle pass 3/3; mutant và no-op fail; alternative pass.
- [ ] Không ép cách giải ngoài hợp đồng; JSON whitespace/key order được chấp nhận.
- [ ] Thiếu artifact là fail; lỗi grader không bị che thành model fail.
- [ ] Test/đáp án không nằm trong agent image; transfer chỉ đúng path.
- [ ] Reviewer khác tác giả xác nhận và ghi tên/ngày; chưa có reviewer thì giữ development.

## Nguồn

- [Harbor config](https://docs.harborframework.com/tasks/configuration)
- [Verifier riêng](https://docs.harborframework.com/tasks/separate-verifier)
- [Artifacts](https://docs.harborframework.com/tasks/artifacts)

Đã đối chiếu ngày 12/11/2026; validate lại bằng package Harbor đã khóa, không chỉ kiểm tra TOML đọc được.
