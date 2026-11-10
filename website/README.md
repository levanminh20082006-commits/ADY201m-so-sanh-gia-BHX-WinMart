# So Giá BHX – WinMart

Website so sánh giá **cùng một sản phẩm** giữa Bách Hóa Xanh và WinMart, giúp người mua biết món nào rẻ hơn ở đâu
và tính tổng tiền giỏ hàng ở mỗi siêu thị.

- **Trang chủ**: tìm kiếm có gợi ý tức thì, dải tin chạy các món chênh giá lớn, số liệu chạy đếm, 7 danh mục, các món tiết kiệm nhiều nhất, khuyến mãi nổi bật (trượt ngang), biểu đồ "nhóm hàng nào nên mua ở đâu".
- **So sánh giá**: 139 cặp sản phẩm giống hệt nhau (cùng thương hiệu, khối lượng, số lượng) có bán ở cả 2 nơi; lọc theo nhóm, theo nơi rẻ hơn.
- **Sản phẩm**: 3.507 sản phẩm có ảnh, lọc theo nhóm / khoảng giá / siêu thị / khuyến mãi / có bán cả 2 nơi, sắp xếp theo giá hoặc giá theo kg/lít.
- **Xem nhanh**: bấm vào ảnh để xem chi tiết, so với siêu thị còn lại và **gợi ý món cùng danh mục rẻ hơn theo kg/lít**.
- **Khuyến mãi**: giảm sâu nhất, flash sale, mua kèm / combo.
- **Thống kê**: biểu đồ tương tác (số sản phẩm, giá trung vị, tỉ lệ khuyến mãi theo nhóm, phân khúc giá, phân bố chênh lệch 139 cặp), có bảng số liệu.
- **Giỏ hàng**: tổng tiền nếu mua hết ở BHX / WinMart / mua tách 2 nơi, số tiền tiết kiệm, sao chép hoặc tải danh sách đi chợ, chia sẻ giỏ hàng bằng link.
- **Theo slide**: minh chứng theo thứ tự bài giảng (loại biến, chuẩn bị dữ liệu, thống kê mô tả, tương quan, kiểm định, 12 biểu đồ Report 4), số liệu tính bằng chính code của Report 3.
- **Yêu thích**, **Giới thiệu** (quy trình dữ liệu, kết quả chính, câu hỏi thường gặp).
- Tìm kiếm không dấu (phím tắt `/`), giao diện sáng / tối, hiệu ứng khi cuộn, dùng tốt trên điện thoại, đường link chia sẻ được đúng bộ lọc.

Ảnh sản phẩm được tải trực tiếp từ máy chủ ảnh của hai siêu thị (đường dẫn lấy từ dữ liệu thu thập).

Giá thu thập ngày 12/10/2026 (đề tài môn ADY201m, FPT). Website không thuộc và không liên kết với hai siêu thị.

## Cập nhật dữ liệu

Dữ liệu trong `data/` được xuất từ dữ liệu đã làm sạch của project (Report 3):

```
.venv\Scripts\python.exe website\tools\build_data.py
```

## Xem trên máy

Trang đọc file JSON nên cần chạy qua web server (mở thẳng file `index.html` sẽ không tải được dữ liệu):

```
cd website
python -m http.server 8000
```

Rồi mở http://localhost:8000
