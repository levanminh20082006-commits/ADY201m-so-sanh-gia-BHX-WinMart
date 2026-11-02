/* ADY201m Report 2 - SQL demo queries for SSMS.
   Mở SSMS → Server: localhost\SQLEXPRESS (Windows Authentication) → mở file này → chạy từng câu (bôi đen + F5).
   Mỗi câu có chú thích tiếng Việt: câu đó làm gì và vì sao cần trong Report 2.
*/
USE ADY201m_Report2;
GO

-- 1) SELECT: xem 20 bản ghi giá mới nhất, kèm tên sản phẩm và siêu thị.
--    JOIN nối bảng giá (PriceObservations) với bảng sản phẩm (Products) qua product_key.
SELECT TOP (20) o.collected_at, p.store_code, p.name, p.brand, o.sale_price_vnd, o.list_price_vnd, p.product_url
FROM dbo.PriceObservations AS o
JOIN dbo.Products AS p ON p.product_key = o.product_key
ORDER BY o.collected_at DESC;

-- 2) COUNT: tổng số bản ghi trong từng bảng → dùng để đối chiếu với CSV.
SELECT 'Stores' AS table_name, COUNT(*) AS row_count FROM dbo.Stores
UNION ALL SELECT 'CollectionRuns', COUNT(*) FROM dbo.CollectionRuns
UNION ALL SELECT 'Products', COUNT(*) FROM dbo.Products
UNION ALL SELECT 'PriceObservations', COUNT(*) FROM dbo.PriceObservations
UNION ALL SELECT 'ProductMatches', COUNT(*) FROM dbo.ProductMatches;

-- 3) DISTINCT: có bao nhiêu thương hiệu khác nhau ở mỗi siêu thị.
SELECT store_code, COUNT(DISTINCT brand) AS distinct_brands
FROM dbo.Products
GROUP BY store_code;

-- 4) WHERE: chỉ lấy sản phẩm đang khuyến mãi (giá niêm yết > giá bán) của Vinamilk.
SELECT p.store_code, p.name, o.list_price_vnd, o.sale_price_vnd
FROM dbo.PriceObservations o JOIN dbo.Products p ON p.product_key = o.product_key
WHERE o.is_promotion = 1 AND p.brand LIKE N'%Vinamilk%'
ORDER BY p.store_code, o.sale_price_vnd;

-- 5) GROUP BY + MIN/MAX/AVG: thống kê giá theo siêu thị.
SELECT p.store_code,
       COUNT(*)                                   AS observations,
       MIN(o.sale_price_vnd)                      AS min_price,
       MAX(o.sale_price_vnd)                      AS max_price,
       CAST(AVG(o.sale_price_vnd) AS decimal(12,0)) AS avg_price,
       SUM(CASE WHEN o.is_promotion = 1 THEN 1 ELSE 0 END) AS on_promotion
FROM dbo.PriceObservations o JOIN dbo.Products p ON p.product_key = o.product_key
GROUP BY p.store_code;

-- 6) GROUP BY theo danh mục + ORDER BY: danh mục nào có nhiều sản phẩm nhất.
SELECT p.store_code, o.category_slug, COUNT(*) AS products, CAST(AVG(o.sale_price_vnd) AS decimal(12,0)) AS avg_price
FROM dbo.PriceObservations o JOIN dbo.Products p ON p.product_key = o.product_key
GROUP BY p.store_code, o.category_slug
ORDER BY products DESC;

-- 7) Thống kê theo thời điểm thu thập: mỗi lần chạy (run) có bao nhiêu giá, thu thập từ mấy giờ đến mấy giờ.
SELECT o.run_id, p.store_code, COUNT(*) AS observations,
       MIN(o.collected_at) AS first_collected, MAX(o.collected_at) AS last_collected
FROM dbo.PriceObservations o JOIN dbo.Products p ON p.product_key = o.product_key
GROUP BY o.run_id, p.store_code
ORDER BY o.run_id, p.store_code;

-- 8) Kiểm tra bản ghi trùng: một sản phẩm không được có 2 giá trong cùng 1 lần chạy.
--    Kết quả mong đợi: 0 dòng (đã có UNIQUE constraint UQ_Obs_RunProduct bảo vệ).
SELECT run_id, product_key, COUNT(*) AS times
FROM dbo.PriceObservations
GROUP BY run_id, product_key
HAVING COUNT(*) > 1;

-- 9) Kiểm tra trùng sản phẩm: cùng siêu thị + cùng mã sản phẩm chỉ có 1 dòng. Mong đợi: 0 dòng.
SELECT store_code, store_product_code, COUNT(*) AS times
FROM dbo.Products GROUP BY store_code, store_product_code HAVING COUNT(*) > 1;

-- 10) Kết quả ghép sản phẩm: bao nhiêu cặp MATCHED / NEEDS_REVIEW.
SELECT run_id, status, COUNT(*) AS pairs
FROM dbo.ProductMatches GROUP BY run_id, status;

-- 11) Bảng so sánh giá chính (view chỉ chứa cặp MATCHED và đủ điều kiện so sánh).
--     price_diff_vnd = Giá WinMart - Giá BHX:  dương → WinMart đắt hơn; âm → WinMart rẻ hơn.
SELECT TOP (30) brand, bhx_name, winmart_name, size_value, size_unit, pack_count,
       bhx_price_vnd, winmart_price_vnd, price_diff_vnd, price_diff_pct, bhx_url, winmart_url
FROM dbo.vw_PriceComparison
ORDER BY ABS(price_diff_pct) DESC;

-- 12) Tóm tắt chênh lệch: bao nhiêu cặp WinMart rẻ hơn / đắt hơn / bằng giá, chênh lệch trung bình %.
SELECT CASE WHEN price_diff_vnd > 0 THEN 'WinMart more expensive'
            WHEN price_diff_vnd < 0 THEN 'WinMart cheaper' ELSE 'Same price' END AS result,
       COUNT(*) AS pairs, CAST(AVG(price_diff_pct) AS decimal(8,2)) AS avg_diff_pct
FROM dbo.vw_PriceComparison
GROUP BY CASE WHEN price_diff_vnd > 0 THEN 'WinMart more expensive'
              WHEN price_diff_vnd < 0 THEN 'WinMart cheaper' ELSE 'Same price' END;

-- 13) Truy vết: từ một giá trong SQL quay về đúng file JSON gốc và vị trí trong file.
SELECT TOP (5) o.observation_id, p.name, o.sale_price_vnd, o.raw_file, o.row_id, o.dom_price_check
FROM dbo.PriceObservations o JOIN dbo.Products p ON p.product_key = o.product_key
ORDER BY NEWID();

-- 14) Lịch sử giá của một sản phẩm qua các lần thu thập (dùng cho Report 3 khi có nhiều run).
SELECT p.store_code, p.name, o.run_id, o.collected_at, o.sale_price_vnd
FROM dbo.PriceObservations o JOIN dbo.Products p ON p.product_key = o.product_key
WHERE p.product_key IN (SELECT TOP (3) product_key FROM dbo.PriceObservations
                        GROUP BY product_key ORDER BY COUNT(*) DESC, product_key)
ORDER BY p.name, o.collected_at;
