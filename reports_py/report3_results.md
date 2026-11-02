# Report 3 - EDA: kết quả (tạo bởi `python -m report3.run`)

## 1. Data understanding - Tìm hiểu dữ liệu đã thu thập

- Nguồn: dữ liệu sạch của Report 2 `clean_observations.csv` (3.507 dòng x 45 cột), lần thu thập run_20261012_1622.

- Thu thập 12/10/2026 16:22 -> 16:43 (+07:00): 1 lần chụp giá = **cross-sectional data** (slide 6.1), không phải time series. Đây là **sample** (7 nhóm hàng, mỗi siêu thị 1 khu vực giá) của **population** là toàn bộ sản phẩm của 2 chuỗi siêu thị (slide 6.2).

- 1 dòng = giá của 1 sản phẩm tại 1 siêu thị. BHX 1.412 dòng, WinMart 2.095 dòng; 54 trang danh mục; 755 thương hiệu.

- Dữ liệu **multivariate** (slide 6.1): mỗi quan sát có 45 biến. Mục 2.2 đến mục 2.4 phân tích **univariate** (từng biến một); mục 2.5 và các biểu đồ scatter của Report 4 phân tích 2 biến cùng lúc.

- Sản phẩm ghép cặp (cùng thương hiệu + khối lượng + số lượng + vị ở cả 2 siêu thị): 139 cặp.

### Số dòng theo nhóm hàng và siêu thị

| group | bhx | winmart | tổng |
|---|---|---|---|
| beverages | 261 | 359 | 620 |
| household_cleaning | 136 | 101 | 237 |
| instant_food | 265 | 249 | 514 |
| milk_dairy | 137 | 298 | 435 |
| personal_care | 228 | 406 | 634 |
| seasoning | 160 | 255 | 415 |
| snacks_confectionery | 225 | 427 | 652 |
| tổng | 1412 | 2095 | 3507 |

### Biến và loại biến (slide 6.1)

| biến | loại biến (slide 6.1) | ý nghĩa | số giá trị khác nhau | % thiếu |
|---|---|---|---|---|
| store | categorical (nominal) | siêu thị: bhx / winmart | 2 | 0,0 |
| group | categorical (nominal) | nhóm hàng, 7 giá trị | 7 | 0,0 |
| category_slug | categorical (nominal) | trang danh mục trên website | 54 | 0,0 |
| brand | categorical (nominal) | thương hiệu | 755 | 0,4 |
| unit_label | categorical (nominal) | đơn vị bán: Gói, Chai, Thùng... | 40 | 0,0 |
| size_unit | categorical (nominal) | g / ml | 2 | 5,4 |
| sale_price_vnd | ratio (số liên tục) | giá bán (VND) - có số 0 thật, 100k = 2 x 50k | 1059 | 0,0 |
| list_price_vnd | ratio (số liên tục) | giá niêm yết trước giảm giá (VND) | 1048 | 0,1 |
| discount_pct | ratio (số liên tục) | % giảm giá = (niêm yết - bán) / niêm yết x 100 | 227 | 0,0 |
| size_value | ratio (số liên tục) | khối lượng / dung tích 1 món (g hoặc ml) | 326 | 5,4 |
| pack_count | ratio (số rời rạc - đếm) | số món trong 1 đơn vị bán | 31 | 5,5 |
| total_quantity | ratio (số liên tục) | khối lượng tổng = size_value x pack_count | 417 | 10,6 |
| unit_price_vnd_per_kg_or_l | ratio (số liên tục, tính ra) | giá trên 1 kg hoặc 1 lít | 2038 | 10,6 |
| stock_qty | ratio (số rời rạc - đếm) | số lượng tồn kho (chỉ WinMart) | 371 | 40,3 |
| is_promotion | categorical (nhị phân có/không) | có khuyến mãi (giá niêm yết > giá bán) | 2 | 0,0 |
| collected_at | interval (thời gian, không có số 0 tự nhiên) | thời điểm thu thập, +07:00 | 54 | 0,0 |
| product_code | categorical (mã định danh, không đem tính) | mã sản phẩm của siêu thị | 3507 | 0,0 |
| barcode | categorical (mã định danh, không đem tính) | mã vạch (chỉ WinMart) | 2095 | 40,3 |

### Loại biến nào dùng chỉ số nào (slide 6.1 / 6.2)

| loại biến | biến trong bài | chỉ số dùng được (slide 6.1 / 6.2) | không dùng được |
|---|---|---|---|
| categorical (nominal) | store, group, brand, unit_label, is_promotion | đếm, tỉ lệ %, mode | mean, median vô nghĩa (không có thứ tự, không có khoảng cách) |
| ordinal | phân khúc giá sau binning: rẻ < trung bình < cao (mục 3.5) | thêm median, so sánh thứ tự | hiệu số, mean vô nghĩa (khoảng cách giữa các bậc không cố định) |
| interval | collected_at (thời điểm) | thêm hiệu số (khoảng thời gian), mean | tỉ số vô nghĩa (không có số 0 tự nhiên) |
| ratio | giá, khối lượng, số lượng trong gói, % giảm giá | tất cả: mean, median, mode, variance, std, range, CV, tỉ số | - |

### Đơn vị bán (8 loại nhiều nhất)

Gói: 1014, Chai: 829, Hộp: 442, Thùng: 272, Lốc: 138, Lon: 119, Gói (Lốc) 4: 107, Tuýp: 86

## 2. Statistics - Các ý nghĩa thống kê

### 2.1 Ý nghĩa các chỉ số (slide 6.2)

| chỉ số | ý nghĩa |
|---|---|
| mean | trung bình = tổng / số quan sát; bị vài sản phẩm rất đắt kéo lên |
| median | giá trị đứng giữa khi xếp từ nhỏ đến lớn; không bị giá trị cực đoan ảnh hưởng -> giá 'điển hình' khi dữ liệu lệch |
| mode | giá trị xuất hiện nhiều nhất; dùng được cả cho biến phân loại |
| range | max - min: độ rộng toàn bộ dữ liệu, rất nhạy với giá trị cực đoan |
| variance | trung bình bình phương khoảng cách tới mean; đơn vị là VND bình phương nên khó đọc trực tiếp |
| std | căn bậc hai của variance, cùng đơn vị VND: giá thường cách trung bình bao nhiêu |
| CV% | std / mean x 100: độ phân tán tương đối, so được giữa các nhóm có mức giá khác nhau |
| Q1, Q3, IQR | mốc 25% / 75%; IQR = Q3 - Q1 = độ rộng 50% dữ liệu ở giữa, bền với outlier |
| skewness | độ lệch: > 0 đuôi dài bên phải (ít món rất đắt); skew lớn hơn 1 (hoặc nhỏ hơn -1) là lệch mạnh |
| kurtosis | pandas tính excess kurtosis (chuẩn = 0); > 3 là nhiều giá trị cực đoan |
| p-value | nếu thật sự không có khác biệt, xác suất thấy chênh lệch lớn như vậy; p < 0,05 = có ý nghĩa thống kê |

### 2.2 Thống kê mô tả (univariate)

Tất cả biến số (ratio) - tương tự df.describe() của slide 2.7:

| biến | n | mean | median | mode | std | variance | min | max | range | skew |
|---|---|---|---|---|---|---|---|---|---|---|
| sale_price_vnd | 3507 | 84.945,5 | 43.500,0 | 12.000,0 | 114.957,0 | 13.215.110.057,0 | 2.600,0 | 1.521.000,0 | 1.518.400,0 | 4,5 |
| list_price_vnd | 3507 | 89.449,4 | 45.400,0 | 12.000,0 | 121.957,4 | 14.873.615.113,0 | 2.600,0 | 1.521.000,0 | 1.518.400,0 | 4,4 |
| discount_pct | 3507 | 3,2 | 0,0 | 0,0 | 8,0 | 64,0 | 0,0 | 50,0 | 50,0 | 2,6 |
| size_value | 3319 | 473,7 | 220,0 | 500,0 | 764,1 | 583.896,2 | 2,0 | 6.000,0 | 5.998,0 | 3,6 |
| pack_count | 3341 | 4,0 | 1,0 | 1,0 | 8,7 | 76,2 | 1,0 | 100,0 | 99,0 | 4,6 |
| total_quantity | 3159 | 1.125,4 | 350,0 | 500,0 | 2.300,1 | 5.290.445,4 | 3,0 | 20.000,0 | 19.997,0 | 4,1 |
| unit_price_vnd_per_kg_or_l | 3159 | 262.778,2 | 126.667,0 | 16.000,0 | 488.582,2 | 238.712.542.436,8 | 4.000,0 | 8.625.000,0 | 8.621.000,0 | 7,4 |
| stock_qty | 2095 | 112,5 | 37,0 | 9,0 | 420,4 | 176.773,7 | 1,0 | 9.602,0 | 9.601,0 | 15,1 |

Giá bán (VND) theo siêu thị:

| store | n | mean | median | mode | std | variance | cv_pct | q1 | q3 | iqr | min | max | range | skew | kurtosis |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bhx | 1412 | 88.380,1 | 37.000,0 | 12.000,0 | 137.667,8 | 18.952.429.808,7 | 155,8 | 16.000,0 | 115.000,0 | 99.000,0 | 3.600,0 | 1.521.000,0 | 1.517.400,0 | 4,6 | 31,5 |
| winmart | 2095 | 82.630,6 | 47.900,0 | 35.000,0 | 96.654,7 | 9.342.127.417,7 | 117,0 | 24.600,0 | 109.450,0 | 84.850,0 | 2.600,0 | 1.226.000,0 | 1.223.400,0 | 3,7 | 26,1 |

Ý nghĩa: giá bán lệch phải mạnh (skew 4,51): vài sản phẩm rất đắt kéo mean lên trên median; đuôi dày, nhiều giá trị cực đoan (excess kurtosis 34,46); dùng median làm giá trị điển hình.

Sau khi lấy log: gần đối xứng (skew 0,07); đuôi gần giống phân phối chuẩn (excess kurtosis -0,62); dùng mean làm giá trị điển hình. -> kiểm định và chuẩn hóa dùng log giá.

### 2.3 Giá bán theo nhóm hàng và siêu thị

| group | store | n | median | iqr | cv_pct |
|---|---|---|---|---|---|
| beverages | bhx | 261 | 47.000,0 | 66.100,0 | 98,5 |
| beverages | winmart | 359 | 46.900,0 | 80.350,0 | 117,8 |
| household_cleaning | bhx | 136 | 113.500,0 | 147.250,0 | 111,6 |
| household_cleaning | winmart | 101 | 117.900,0 | 148.000,0 | 67,4 |
| instant_food | bhx | 265 | 15.600,0 | 103.200,0 | 209,9 |
| instant_food | winmart | 249 | 25.700,0 | 64.800,0 | 138,6 |
| milk_dairy | bhx | 137 | 37.000,0 | 166.000,0 | 123,7 |
| milk_dairy | winmart | 298 | 38.050,0 | 49.350,0 | 179,8 |
| personal_care | bhx | 228 | 119.000,0 | 114.750,0 | 72,4 |
| personal_care | winmart | 406 | 105.000,0 | 121.775,0 | 69,0 |
| seasoning | bhx | 160 | 33.500,0 | 48.675,0 | 202,2 |
| seasoning | winmart | 255 | 49.900,0 | 67.400,0 | 109,7 |
| snacks_confectionery | bhx | 225 | 22.000,0 | 18.500,0 | 125,1 |
| snacks_confectionery | winmart | 427 | 34.900,0 | 40.900,0 | 114,4 |

### 2.4 Giá trên kg / lít (chỉ các dòng biết khối lượng thật)

| store | n | mean | median | mode | std | variance | cv_pct | q1 | q3 | iqr | min | max | range | skew | kurtosis |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bhx | 1326 | 175.894,0 | 98.680,5 | 187.500,0 | 297.344,6 | 88.413.799.897,6 | 169,0 | 40.579,0 | 214.286,0 | 173.707,0 | 4.000,0 | 3.700.000,0 | 3.696.000,0 | 6,0 | 48,1 |
| winmart | 1833 | 325.630,7 | 156.818,0 | 1.590.909,0 | 581.489,9 | 338.130.446.358,5 | 178,6 | 65.077,0 | 333.651,0 | 268.574,0 | 5.500,0 | 8.625.000,0 | 8.619.500,0 | 6,7 | 68,5 |

### 2.5 Correlation - Tương quan (Spearman, thang log)

|  | log price | log list price | discount % | log size | pack count | log total qty | log unit price |
|---|---|---|---|---|---|---|---|
| log price | 1,00 | 1,00 | 0,18 | 0,43 | 0,30 | 0,59 | 0,22 |
| log list price | 1,00 | 1,00 | 0,25 | 0,44 | 0,30 | 0,60 | 0,20 |
| discount % | 0,18 | 0,25 | 1,00 | 0,28 | 0,10 | 0,30 | -0,20 |
| log size | 0,43 | 0,44 | 0,28 | 1,00 | -0,15 | 0,75 | -0,45 |
| pack count | 0,30 | 0,30 | 0,10 | -0,15 | 1,00 | 0,50 | -0,38 |
| log total qty | 0,59 | 0,60 | 0,30 | 0,75 | 0,50 | 1,00 | -0,63 |
| log unit price | 0,22 | 0,20 | -0,20 | -0,45 | -0,38 | -0,63 | 1,00 |

Gói càng lớn càng đắt: Spearman r = 0,72 ở BHX (mạnh), 0,49 ở WinMart (trung bình), cả hai CÓ ý nghĩa thống kê (p < 0,05). Khối lượng tổng và giá trên kg tương quan âm: mua gói lớn rẻ hơn trên mỗi kg. Tương quan không phải nhân quả.

### 2.6 Significance tests - Kiểm định ý nghĩa thống kê (alpha = 0,05)

**H1. Tỉ lệ sản phẩm khuyến mãi của 2 siêu thị có khác nhau không?** Chi-square 2x2: chi2 = 109,7, p = 1,2e-25 -> CÓ ý nghĩa thống kê (p < 0,05). Tỉ lệ khuyến mãi BHX 24,6% vs WinMart 11,2%; mức giảm trung bình khi có khuyến mãi BHX 20,2%, WinMart 18,0%.

**H2. Giá trên kệ hàng có khác nhau không (mọi sản phẩm, không ghép cặp)?** Mann-Whitney U: z = 4,57, p = 4,8e-06 -> CÓ ý nghĩa thống kê (p < 0,05); P(giá WinMart > giá BHX) = 0,55. Lưu ý: 2 siêu thị bán khác mặt hàng, khác quy cách, nên đây là so sánh cơ cấu kệ hàng, không phải giá của cùng một sản phẩm.

**H3. Cùng một sản phẩm thì nơi nào rẻ hơn? (139 cặp ghép)** WinMart rẻ hơn 65, đắt hơn 65, bằng giá 9. Chênh lệch trung vị 0,0%, trung bình 1,20%. Paired t-test trên log(WinMart / BHX): t = 0,66, p = 0,51; sign test chính xác p = 1,00; chênh lệch trung bình hình học +0,61% (khoảng tin cậy 95% bootstrap -1,13% đến +2,45%) -> KHÔNG có ý nghĩa thống kê (p ≥ 0,05): không siêu thị nào rẻ hơn một cách có hệ thống.

Kiểm định 139 cặp theo nhóm hàng (sign test; nhóm có ít cặp không thể đạt ý nghĩa thống kê):

| group | pairs | winmart_cheaper | winmart_more_expensive | median_diff_pct | mean_diff_pct | sign_test_p |
|---|---|---|---|---|---|---|
| instant_food | 52 | 21 | 24 | 0,00 | -0,67 | 0,77 |
| seasoning | 31 | 19 | 11 | -2,16 | -0,66 | 0,20 |
| milk_dairy | 23 | 10 | 12 | 2,30 | -0,48 | 0,83 |
| beverages | 15 | 7 | 8 | 5,56 | 6,31 | 1,00 |
| snacks_confectionery | 11 | 7 | 4 | -1,50 | -1,35 | 0,55 |
| household_cleaning | 4 | 1 | 3 | 19,80 | 18,32 | 0,62 |
| personal_care | 3 | 0 | 3 | 24,18 | 26,63 | 0,25 |

## 3. Data preprocessing - Xử lý dữ liệu

Đầu ra: `data/processed_py/report3_prepared.csv` (3.507 dòng, không xóa dòng nào; file của Report 2 không bị sửa).

Kiểm tra trùng lặp (slide 2.3 - data preparation loại bỏ dòng trùng): Report 2 đã loại 200 dòng trùng; kiểm tra lại trên dữ liệu đầu vào Report 3:

| kiểm tra | số dòng trùng |
|---|---|
| trùng row_id (cùng vị trí trong file gốc) | 0 |
| trùng (siêu thị, mã sản phẩm) | 0 |
| trùng toàn bộ nội dung dòng | 0 |

### 3.1 Fix wrong values - Sửa giá trị sai (pack count)

Đã sửa 41 giá trị: 27 lấy theo đơn vị bán (lốc), 13 số là một phần của tên sản phẩm, 1 dạng 'số x khối lượng'. Một con số trong tên sản phẩm bị đọc nhầm thành số lượng (vd 'Wake Up 247' -> 247 lon, giá 141 đ/lít); WinMart bán lốc 6 ('Gói (Lốc) 6') nhưng tên ghi 'Thùng 24' -> giá là của đơn vị bán; '25*20g' -> 25 gói.

| store | name | pack_fix | new_pack |
|---|---|---|---|
| bhx | Nước tăng lực Wake Up 247 vị cà phê 330ml | number_is_part_of_name | 1,0 |
| winmart | Dầu gội dược liệu Thái Dương 7+ chai 250ml | number_is_part_of_name | 1,0 |
| winmart | Lưỡi dao cạo Gillette Mach 3+ gói 6 cái | number_is_part_of_name | 1,0 |
| winmart | Nước uống sữa trái cây bổ dưỡng hương dâu Nutri Boost thùng 24 chai x 297ml | selling_unit_label | 6,0 |
| winmart | Thùng 24 lon nước ngọt 7UP 330ml | selling_unit_label | 6,0 |
| winmart | Thùng 24 lon nước tăng lực STING hương dâu 330ml/320ml | selling_unit_label | 6,0 |
| winmart | Cà phê phố sữa đá MacCoffee (24gx10) 240g | number_is_part_of_name | 1,0 |
| winmart | Café xay Sáng Tạo 8 Trung Nguyên hộp 500g | number_is_part_of_name | 1,0 |
| winmart | Cà phê rang xay Sáng Tạo 2 Trung Nguyên gói 340g | number_is_part_of_name | 1,0 |
| winmart | Cà phê rang xay Sáng Tạo 4 Trung Nguyên gói 340g | number_is_part_of_name | 1,0 |
| winmart | Cà phê Sáng Tạo số 3 Trung Nguyên gói 340g | number_is_part_of_name | 1,0 |
| winmart | Cà phê chế phin 5 Trung Nguyên gói 500g | number_is_part_of_name | 1,0 |
| winmart | Café sữa đá Nescafe 25*20g | n_x_size_in_name | 25,0 |
| winmart | Thùng 24 chai nước tăng lực nhân sâm Sting 330ml | selling_unit_label | 6,0 |
| winmart | Thùng 24 chai nước tăng lực Sting hương dâu tây đỏ 330ml | selling_unit_label | 6,0 |

### 3.2 Missing values - Xử lý giá trị thiếu

Hai loại: **thiếu do cấu trúc** (website không công bố, hoặc sự kiện không xảy ra -> không phải lỗi, để trống) và **thiếu thật** (thông tin có nhưng không đọc được -> chỉ điền khi có quy tắc an toàn, luôn kèm cột cờ). Các cách xử lý theo slide 2.6: drop, thay bằng giá trị trung tâm / tần suất (mode), thay theo quy tắc, để nguyên.

| column | missing_total | bhx_pct | winmart_pct | type | note | decision |
|---|---|---|---|---|---|---|
| dom_promo_line | 3492 | 100,00 | 99,28 | thiếu do cấu trúc | no promotion line on the card | để trống (không áp dụng) |
| flash_sale_price_vnd | 3440 | 95,25 | 100,00 | thiếu do cấu trúc | no flash sale on this product | -> cột có/không is_flash_sale |
| flash_sale_start | 3440 | 95,25 | 100,00 | thiếu do cấu trúc | no flash sale on this product | để trống (không áp dụng) |
| flash_sale_end | 3440 | 95,25 | 100,00 | thiếu do cấu trúc | no flash sale on this product | để trống (không áp dụng) |
| spec_flavor | 3403 | 92,63 | 100,00 | thiếu do cấu trúc | flavour not listed | để trống (không áp dụng) |
| warnings | 3119 | 93,84 | 85,63 | thiếu do cấu trúc | no warning for this row | để trống (không áp dụng) |
| promotion_text | 2967 | 78,12 | 88,97 | thiếu do cấu trúc | no promotion text shown | để trống (không áp dụng) |
| site_item_no | 1412 | 100,00 | 0,00 | thiếu do cấu trúc | BHX has no WinMart item number | để trống (không áp dụng) |
| barcode | 1412 | 100,00 | 0,00 | thiếu do cấu trúc | BHX does not publish barcodes | để trống (không áp dụng) |
| stock_qty | 1412 | 100,00 | 0,00 | thiếu do cấu trúc | BHX does not publish stock | để trống (không áp dụng) |
| total_quantity | 373 | 6,09 | 13,70 | thiếu thật |  | tính lại sau khi sửa; trống khi thiếu khối lượng / số lượng |
| unit_price_vnd_per_kg_or_l | 373 | 6,09 | 13,70 | thiếu thật |  | tính lại sau khi sửa; trống khi thiếu khối lượng / số lượng |
| pack_count | 193 | 4,46 | 6,21 | thiếu thật |  | điền 1 (mode, 74% số dòng) vào pack_count_filled + cột cờ |
| size_unit | 188 | 1,70 | 7,83 | thiếu thật |  | để trống (không đoán được) |
| size_source | 188 | 1,70 | 7,83 | thiếu thật |  | để trống |
| size_value | 188 | 1,70 | 7,83 | thiếu thật |  | không bịa cho giá/kg; median theo siêu thị + danh mục (log) chỉ ở log_size_filled + cột cờ |
| pack_source | 161 | 4,46 | 4,68 | thiếu thật |  | để trống |
| brand | 13 | 0,07 | 0,57 | thiếu thật |  | điền 'UNKNOWN' + cột cờ |
| brand_key | 13 | 0,07 | 0,57 | thiếu thật |  | điền 'unknown' |
| list_price_vnd | 2 | 0,00 | 0,10 | thiếu thật |  | điền = giá bán (không có khuyến mãi) |

Đã điền: giá niêm yết 2 ô, thương hiệu 13 ô, số lượng trong gói 166 ô, khối lượng 188 ô (chỉ ở cột đặc trưng cho mô hình). Giá/kg-lít có cho 3.159 dòng. Ô trống còn lại trong 4 cột đặc trưng (log_price, discount_pct, log_size_filled, pack_count_filled): 0.

### 3.3 Outliers - Giá trị ngoại lai (quy tắc IQR trong từng nhóm hàng)

Chỉ đánh dấu, không xóa: theo giá gốc 297 dòng, theo log giá 49 dòng, theo log giá/kg 124 dòng. Đây là giá thật (thùng 12-40 món, mỹ phẩm, yến) nên xóa sẽ làm lệch dữ liệu; lấy log để giảm ảnh hưởng.

| store | group | name_clean | sale_price_vnd |
|---|---|---|---|
| winmart | milk_dairy | Sữa bột Abbott PediaSure BA hương vani 1,6kg | 1226000 |
| winmart | milk_dairy | Lon Ensure Gold Green Health Đạm thực vật 850g | 993000 |
| winmart | milk_dairy | Sữa Glucerna Hương Lúa Mạch hộp 850g | 967000 |
| winmart | milk_dairy | Sữa bột Abbott Glucerna hương vani hộp 850g | 965000 |
| bhx | seasoning | 12 chai dầu gạo lứt Simply 1 lít | 924000 |

### 3.4 Normalisation - Chuẩn hóa (slide 2.6)

- Log: `log(x)` - đưa giá lệch phải về gần đối xứng (skew 4,51 -> 0,07).
- Simple feature scaling: `x / max` -> giá trị trong (0, 1]; cách đơn giản nhất trong slide 2.6, giữ tỉ lệ giữa các giá trị.
- Min-max: `(x - min) / (max - min)` -> khoảng [0, 1]; nhạy với giá trị cực đoan.
- Z-score: `(x - mean) / std` -> mean 0, std 1; tốt nhất sau khi lấy log, khi dữ liệu gần chuẩn.
- Robust: `(x - median) / IQR` -> không bị outlier ảnh hưởng; không dùng được khi IQR = 0 (discount_pct và pack_count: 75% số dòng có cùng giá trị).

Tham số (lưu lại để dữ liệu mới được chuẩn hóa đúng như cũ):

| feature | min | max | mean | std | median | iqr |
|---|---|---|---|---|---|---|
| log_price | 7,863 | 14,235 | 10,737 | 1,123 | 10,681 | 1,697 |
| discount_pct | 0,000 | 50,000 | 3,196 | 8,001 | 0,000 | 0,000 |
| log_size_filled | 0,693 | 8,700 | 5,406 | 1,202 | 5,394 | 1,609 |
| pack_count_filled | 1,000 | 100,000 | 3,833 | 8,542 | 1,000 | 0,000 |

Kiểm tra trên log giá:

| column | mean | std | min | max |
|---|---|---|---|---|
| log_price | 10,737 | 1,123 | 7,863 | 14,235 |
| log_price_minmax | 0,451 | 0,176 | 0,000 | 1,000 |
| log_price_z | 0,000 | 1,000 | -2,559 | 3,114 |
| log_price_robust | 0,034 | 0,662 | -1,660 | 2,094 |
| log_price_simple_scaling | 0,754 | 0,079 | 0,552 | 1,000 |

### 3.5 Binning and encoding - Chia khoảng và mã hóa (slide 2.6)

Binning: giá bán chia thành 3 khoảng -> biến số trở thành biến **ordinal** (rẻ < trung bình < cao). Dùng cho biểu đồ của Report 4.

| phân khúc giá | bhx | winmart | tổng |
|---|---|---|---|
| low (< 20k) | 436 | 420 | 856 |
| medium (20k - 100k) | 593 | 1107 | 1700 |
| high (>= 100k) | 383 | 568 | 951 |
| tổng | 1412 | 2095 | 3507 |

Dummy variables: is_promotion, is_flash_sale -> 0/1; store và group -> các cột one-hot (store_bhx, store_winmart, group_*), vì mô hình thống kê không nhận chữ.
