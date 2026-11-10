# Phân tích và so sánh giá sản phẩm giữa Bách Hóa Xanh và WinMart

Đề tài môn **ADY201m** – Trường Đại học FPT. Toàn bộ project viết bằng **Python + SQL Server**.

**Câu hỏi của đề tài:** cùng một sản phẩm thì Bách Hóa Xanh (BHX) hay WinMart rẻ hơn?

| Phần | Nội dung | Kết quả chính |
|---|---|---|
| **Report 2** – Thu thập & lưu trữ | Thu thập giá từ website công khai của 2 siêu thị, làm sạch, ghép cặp cùng sản phẩm, lưu SQL Server | 3.507 sản phẩm (BHX 1.412, WinMart 2.095), 139 cặp cùng sản phẩm |
| **Report 3** – EDA | Tìm hiểu dữ liệu, ý nghĩa thống kê, kiểm định; xử lý giá trị sai, missing value, outlier, normalize, binning, encoding | 3.507 × 45 → 3.507 × 83 cột, không xóa dòng nào |
| **Report 4** – Trực quan hóa | 12 biểu đồ thống kê (column, bar, stacked, pie, histogram, boxplot, scatter) kèm nhận xét | 65 cặp rẻ hơn ở BHX, 65 cặp rẻ hơn ở WinMart, 9 cặp bằng giá |
| **Website** | Trang so sánh giá cho người mua: so cùng sản phẩm, tìm kiếm, giỏ hàng, thống kê | Xem mục [Website](#website) |

**Kết luận:** cùng một sản phẩm thì không siêu thị nào rẻ hơn một cách có hệ thống; khoảng 74% số cặp chênh nhau không quá 10%.

## Xem nhanh kết quả

| Nội dung | Mở |
|---|---|
| Kết quả Report 3 (thống kê, kiểm định, xử lý dữ liệu) | [reports_py/report3_results.md](reports_py/report3_results.md) |
| Kết quả Report 4 (12 biểu đồ và nhận xét) | [reports_py/report4_results.md](reports_py/report4_results.md) |
| 12 biểu đồ trên một ảnh | [report4_tong_hop_12_bieu_do.png](reports_py/report4_tong_hop_12_bieu_do.png) |
| Chất lượng dữ liệu Report 2 | [reports_py/data_quality_report.md](reports_py/data_quality_report.md) |
| 139 cặp cùng sản phẩm | [data/processed_py/matched_products.csv](data/processed_py/matched_products.csv) |
| Dữ liệu sau xử lý | [data/processed_py/report3_prepared.csv](data/processed_py/report3_prepared.csv) |
| Website | [website/](website/) |

## Thành viên & đóng góp

| Thành viên | Vai trò | Phần phụ trách |
|---|---|---|
| Lê Văn Minh | **Thực hiện toàn bộ phần kỹ thuật** | Thu thập, làm sạch, ghép cặp, SQL Server, Report 3, Report 4, website, test tự động |

Toàn bộ code và kết quả trong kho này do Lê Văn Minh thực hiện và đưa lên GitHub.

## Luồng dữ liệu

```
websites ──► report2/collect.py ──► data/raw_py/<run>/*.json                 (dữ liệu gốc)
         ──► report2/clean.py   ──► data/processed_py/clean_observations.csv  (+ rejected_rows.csv)
         ──► report2/matching.py──► data/processed_py/matched_products.csv    (139 cặp cùng sản phẩm)
         ──► report2/storage.py ──► SQL Server ADY201m_Report2
         ──► report3/run.py     ──► data/processed_py/report3_prepared.csv + reports_py/report3_results.md
         ──► report3/evidence.py──► evidence/report3/*.csv, *.png
         ──► report4/visualize.py─► reports_py/report4/*.png + reports_py/report4_results.md
         ──► website/tools/build_data.py ──► website/data/*.json ──► website/
```

## 1. Cài đặt (Windows, PowerShell)

```powershell
cd ADY201m_Python
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PLAYWRIGHT_BROWSERS_PATH = "0"          # Chromium nằm trong .venv
.\.venv\Scripts\python.exe -m playwright install chromium
```

SQL Server: `localhost\SQLEXPRESS`, đăng nhập Windows (không có mật khẩu trong code). Cấu hình qua biến môi trường – xem `.env.example`.

## 2. Report 2 – Thu thập và lưu trữ

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = "0"
$py = ".\.venv\Scripts\python.exe"

& $py -m report2.collect                       # ~25-40 phút, nghỉ 5 giây giữa các trang
& $py -m report2.clean                         # tất cả lần thu thập -> CSV sạch + báo cáo chất lượng
& $py -m report2.matching                      # lần thu thập mới nhất -> các cặp cùng sản phẩm
& $py -m report2.storage                       # -> SQL Server (ADY201m_Report2)
& $py -m report2.reconcile                     # đối soát JSON = CSV = SQL
& $py -m report2.verify_samples --n 10         # mở 10 cặp trên website thật để kiểm tra
```

Lần đầu tạo database: `& $py -m report2.storage --create-database`
(code từ chối nếu database đã tồn tại, và từ chối mọi tên không bắt đầu bằng `ADY201m_Report2`).

## 3. Report 3 – EDA và Report 4 – Trực quan hóa

```powershell
& $py -m report3.run              # 3 mục Report 3 -> reports_py/report3_results.md + data/processed_py/report3_prepared.csv
& $py -m report3.evidence         # bảng và hình bằng chứng -> evidence/report3/
& $py -m report4.visualize        # 12 biểu đồ -> reports_py/report4/ + reports_py/report4_results.md
```

## 4. Test tự động

```powershell
$env:ADY_RUN_DB_TESTS = "1"     # chạy cả test SQL (chỉ dùng database ADY201m_Report2_Test)
& $py -m pytest
```

## 5. Notebook và SQL

```powershell
& $py notebooks\build_notebook.py
& $py -m jupyter notebook notebooks\Report2_Data_Collection_Storage.ipynb
```
SSMS: mở `sql/02_demo_queries.sql` (truy vấn demo) và `sql/03_bai_tap.sql` (bài tập truy vấn).

## Website

Trang so sánh giá tĩnh (HTML/CSS/JavaScript), dữ liệu lấy từ kết quả Report 3. Chi tiết và cách đăng GitHub Pages: [website/README.md](website/README.md).

```powershell
& $py website\tools\build_data.py          # cập nhật dữ liệu cho website
cd website; python -m http.server 8000     # xem trên máy: http://localhost:8000
```

## Cấu trúc thư mục

| Đường dẫn | Nội dung |
|---|---|
| `report2/` | Code Report 2: thu thập, làm sạch, ghép cặp, SQL Server, đối soát |
| `report3/` | Code Report 3: tiền xử lý, thống kê, kiểm định, xuất bằng chứng |
| `report4/` | Code Report 4: 12 biểu đồ |
| `website/` | Website so sánh giá |
| `config/` | Danh mục thu thập, bảng tên thương hiệu khác nhau giữa 2 siêu thị |
| `sql/` | Schema, truy vấn demo, bài tập truy vấn |
| `data/raw_py/` | Dữ liệu gốc dạng JSON (bằng chứng) |
| `data/processed_py/` | CSV sạch, bị loại, ghép cặp, dữ liệu sau Report 3 |
| `reports_py/` | Báo cáo chất lượng, kết quả Report 3, kết quả và biểu đồ Report 4 |
| `evidence/` | robots.txt, nhật ký test, nhật ký SQL, bằng chứng Report 3 |
| `docs/report2/` | Báo cáo Report 2, từ điển dữ liệu, báo cáo chất lượng dữ liệu |
| `notebooks/` | Jupyter notebook |
| `tests/python/` | Test tự động (pytest) |
