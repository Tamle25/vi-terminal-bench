# Đặc tả benchmark v0.1

Ngày: 12/11/2026. Trạng thái: native-six development đã kiểm định kỹ thuật, chưa phải bản phát hành hoặc pilot model.

## Mục tiêu

Đo khả năng hoàn thành công việc terminal theo tiếng Việt, chấm artifact thực tế. Đơn vị đánh giá là model + agent + công cụ + ngân sách; không đồng nhất với năng lực model độc lập.

- A: thay ngôn ngữ instruction, giữ nguyên dữ liệu/môi trường/verifier. Bốn biến thể `en`, `vi`, `vi_ascii`, `vi_mixed`.
- B: task viết mới về dữ liệu Việt Nam; hai instruction `en`, `vi`; dữ liệu Việt Nam giữ nguyên.
- Không gộp A/B thành một điểm. Linux container là phạm vi đầu tiên.

## Các mốc

M1 có hai task B, oracle và kiểm định verifier. M2 có 6 task A và 6 task B; mỗi điều kiện chạy 3 lần trên hai cấu hình, tổng 216 trial. Mục tiêu dài hạn 66 A và 30 B chỉ thực hiện sau khi xác minh nguồn, chất lượng và chi phí.

| Nhóm B | Pilot | Trạng thái |
|---|---|---|
| Số, tiền, ngày giờ | b001-vn-invoice | Triển khai đầu tiên |
| Unicode/tên file | b002-unicode-files | Triển khai đầu tiên |
| Chuyển bảng mã | b003-windows1258 | Đã kiểm định kỹ thuật |
| Tìm kiếm/chuẩn hóa | b004-accent-search | Đã kiểm định kỹ thuật |
| Sắp xếp/đối chiếu | b005-vietnamese-collation | Đã kiểm định kỹ thuật |
| CSV/log/pipeline | b006-vietnamese-csv-export | Đã kiểm định kỹ thuật; CSV |

## Điều kiện đạt

Reward chính 0/1, chỉ pass nếu mọi điều kiện công bố được đáp ứng. Lời tự nhận hoàn thành không có giá trị chấm. Sáu task đầu là bài tạo artifact cố định, không yêu cầu viết CLI dùng cho hidden input. Verifier không chạy code agent tạo và không chấm cách dùng thư viện.

Task có card, schema, oracle, negative controls, nguồn và trạng thái review. Nội dung JSON được so theo cấu trúc, kiểm tra kiểu dữ liệu chính xác, không ép thứ tự key hay khoảng trắng. Unicode/byte chỉ so nghiêm ngặt ở nơi hợp đồng yêu cầu.

## Baseline và quyền sử dụng

Người dùng xác nhận ngày 12/11/2026: chưa có snapshot/cấu hình Eval và chưa chọn model/ngân sách. Phần A và paid model runs chưa bắt đầu. Tiếp tục task B và oracle/no-op không cần thông tin này.

Không đưa task LILT hoặc Terminal-Bench vào dataset hiện tại. Trước kế thừa cần xác minh snapshot, giấy phép từng thành phần và tài nguyên. LILT hiện chỉ là nguồn tham khảo phương pháp.

## Các giới hạn phải công bố

Fixture nhỏ, công khai cho development; chưa chứng minh độ khó hoặc khả năng phân biệt model. Sáu task cùng tác giả chưa có reviewer độc lập. Không gọi oracle/negative controls là kết quả đánh giá model. Cấu hình Docker/Linux không đại diện Windows/macOS. Không phát hành v1.0 trước kiểm định, review và pilot.
