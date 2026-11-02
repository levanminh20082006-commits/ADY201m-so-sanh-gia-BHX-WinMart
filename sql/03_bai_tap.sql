/* ADY201m Report 2 - BÀI TẬP TRUY VẤN SQL (SQL Server / T-SQL)
   Dữ liệu: database ADY201m_Report2 (giá sữa Bách Hóa Xanh vs WinMart).

   Các bảng:
     Stores(store_code, store_name, website)
     CollectionRuns(run_id, started_at, finished_at, pages_total, pages_ok, raw_folder, loaded_at)
     Products(product_key, store_code, store_product_code, barcode, name, brand,
              size_value, size_unit, pack_count, unit_label, product_url, first_seen_run, last_seen_run)
     PriceObservations(observation_id, run_id, product_key, collected_at, category_slug,
              sale_price_vnd, list_price_vnd, is_promotion, flash_sale_price_vnd,
              price_store_id, price_area, dom_price_check, source_url, raw_file, row_id)
     ProductMatches(match_id, run_id, status, reason, name_similarity, bhx_observation_id,
              winmart_observation_id, price_diff_vnd, price_diff_pct, price_comparable)
     View vw_PriceComparison (các cặp MATCHED đã so sánh được giá)

   Cách làm: PHẦN A là đề bài - tự viết câu truy vấn trước.
             PHẦN B là đáp án gợi ý - chỉ xem sau khi làm xong.
   Tất cả câu đều chỉ ĐỌC dữ liệu (riêng câu 26 chạy trong transaction rồi ROLLBACK).
*/

/* =====================================================================================
   PHẦN A - ĐỀ BÀI
   =====================================================================================

   ── MỨC 1: SELECT, WHERE, ORDER BY ──────────────────────────────────────────────────
   Câu 1.  Liệt kê mã, tên và website của tất cả siêu thị.
   Câu 2.  Lấy 10 sản phẩm của WinMart CÓ mã vạch (barcode), sắp xếp theo tên A → Z.
   Câu 3.  Tìm các sản phẩm đóng gói theo ml có dung tích mỗi đơn vị từ 1000 ml trở lên.
   Câu 4.  Tìm các sản phẩm có tên chứa cụm "Sữa chua" (lưu ý tiếng Việt có dấu → dùng N'...').
   Câu 5.  Liệt kê sản phẩm bị THIẾU thương hiệu (brand rỗng), hiện siêu thị, tên, link.
   Câu 6.  Lấy 15 bản ghi giá rẻ nhất có giá bán trong khoảng 20.000 – 50.000 đ.
   Câu 7.  Liệt kê sản phẩm có đơn vị bán là 'Lốc' hoặc 'Thùng'.

   ── MỨC 2: Biểu thức, hàm, CASE ─────────────────────────────────────────────────────
   Câu 8.  Với các bản ghi đang khuyến mãi, tính % giảm giá = (giá niêm yết - giá bán) / giá niêm yết * 100.
           Lấy 10 sản phẩm giảm sâu nhất.
   Câu 9.  Với mỗi lần thu thập (CollectionRuns): thời gian chạy bao nhiêu phút, tỉ lệ % trang thành công.
   Câu 10. Tính "giá trên 100 ml/100 g" của mỗi sản phẩm
           = giá bán / (size_value * số đơn vị trong gói) * 100   (pack_count NULL thì coi là 1).
           Lấy 10 sản phẩm có giá/100 đơn vị rẻ nhất, hiện cả siêu thị.
   Câu 11. Liệt kê các bản ghi BHX có giá flash sale, kèm số tiền chênh giữa giá bán thường và giá flash sale.
   Câu 12. Chia bản ghi giá thành 3 nhóm: 'Rẻ' (< 20.000), 'Trung bình' (20.000 – 100.000), 'Cao' (> 100.000).
           Đếm số bản ghi mỗi nhóm theo từng siêu thị.

   ── MỨC 3: GROUP BY, HAVING ─────────────────────────────────────────────────────────
   Câu 13. Đếm số sản phẩm của từng thương hiệu ở mỗi siêu thị, chỉ giữ thương hiệu có từ 5 sản phẩm trở lên.
   Câu 14. Với mỗi danh mục (category_slug): giá trung bình và tỉ lệ % bản ghi đang khuyến mãi.
           Chỉ giữ danh mục có tỉ lệ khuyến mãi > 30%.
   Câu 15. Đếm số bản ghi theo kết quả kiểm tra giá trên trang (dom_price_check) cho từng siêu thị.
   Câu 16. Tìm các thương hiệu có mặt ở CẢ HAI siêu thị.
   Câu 17. WinMart có sản phẩm nào bị trùng mã vạch (cùng barcode nhưng khác sản phẩm) không?

   ── MỨC 4: JOIN, NOT EXISTS ─────────────────────────────────────────────────────────
   Câu 18. Hiện TÊN siêu thị (không phải mã) cùng tổng số bản ghi giá và giá bán trung bình.
   Câu 19. Tìm sản phẩm chưa có bất kỳ bản ghi giá nào (gợi ý: LEFT JOIN ... IS NULL).
   Câu 20. Không dùng view, liệt kê các cặp NEEDS_REVIEW: tên sản phẩm BHX, tên sản phẩm WinMart,
           độ giống tên (name_similarity), lý do. Sắp xếp độ giống giảm dần.
   Câu 21. Trong lần chạy mới nhất, những sản phẩm BHX nào KHÔNG được ghép cặp với WinMart?

   ── MỨC 5: Subquery, CTE, Window function ───────────────────────────────────────────
   Câu 22. Tìm các bản ghi có giá bán cao hơn giá trung bình của CHÍNH danh mục đó (subquery tương quan).
   Câu 23. Top 3 sản phẩm đắt nhất của mỗi siêu thị trong lần chạy mới nhất (ROW_NUMBER).
   Câu 24. Dùng view vw_PriceComparison: với mỗi thương hiệu, đếm số cặp WinMart rẻ hơn / đắt hơn,
           chênh lệch % trung bình, rồi xếp hạng thương hiệu theo mức WinMart rẻ hơn (RANK).
   Câu 25. Theo dõi biến động giá: với mỗi sản phẩm, so giá lần này với lần thu thập trước (LAG).
           Chỉ hiện những dòng giá có thay đổi.
   Câu 26. Bảng so sánh giá trung bình theo thương hiệu dạng 2 cột: avg_bhx | avg_winmart
           (gợi ý: AVG(CASE WHEN ... ) hoặc PIVOT), chỉ lấy thương hiệu có ở cả hai bên.

   ── MỨC 6: Ràng buộc dữ liệu & transaction ──────────────────────────────────────────
   Câu 27. Trong một transaction (rồi ROLLBACK để không làm bẩn dữ liệu), thử INSERT một sản phẩm
           có size_unit = 'kg'. Quan sát lỗi và giải thích ràng buộc nào đã chặn.
*/


/* =====================================================================================
   PHẦN B - ĐÁP ÁN GỢI Ý  (bôi đen từng câu + F5 trong SSMS)
   ===================================================================================== */
USE ADY201m_Report2;
GO

-- Câu 1
SELECT store_code, store_name, website
FROM dbo.Stores;

-- Câu 2
SELECT TOP (10) store_product_code, barcode, name, brand
FROM dbo.Products
WHERE store_code = 'winmart' AND barcode IS NOT NULL
ORDER BY name;

-- Câu 3
SELECT store_code, name, size_value, size_unit, pack_count
FROM dbo.Products
WHERE size_unit = 'ml' AND size_value >= 1000
ORDER BY size_value DESC;

-- Câu 4
SELECT store_code, name, brand
FROM dbo.Products
WHERE name LIKE N'%Sữa chua%';

-- Câu 5
SELECT store_code, name, product_url
FROM dbo.Products
WHERE brand IS NULL OR LTRIM(RTRIM(brand)) = N'';

-- Câu 6
SELECT TOP (15) p.store_code, p.name, o.sale_price_vnd
FROM dbo.PriceObservations o
JOIN dbo.Products p ON p.product_key = o.product_key
WHERE o.sale_price_vnd BETWEEN 20000 AND 50000
ORDER BY o.sale_price_vnd;

-- Câu 7
SELECT store_code, name, unit_label, pack_count
FROM dbo.Products
WHERE unit_label IN (N'Lốc', N'Thùng')
ORDER BY unit_label, store_code;

-- Câu 8  (nhân 100.0 để tránh chia số nguyên)
SELECT TOP (10) p.store_code, p.name, o.list_price_vnd, o.sale_price_vnd,
       CAST((o.list_price_vnd - o.sale_price_vnd) * 100.0 / o.list_price_vnd AS decimal(5,1)) AS discount_pct
FROM dbo.PriceObservations o
JOIN dbo.Products p ON p.product_key = o.product_key
WHERE o.is_promotion = 1 AND o.list_price_vnd > 0
ORDER BY discount_pct DESC;

-- Câu 9
SELECT run_id, started_at, finished_at,
       DATEDIFF(MINUTE, started_at, finished_at)                           AS duration_min,
       pages_ok, pages_total,
       CAST(pages_ok * 100.0 / NULLIF(pages_total, 0) AS decimal(5,1))     AS success_pct
FROM dbo.CollectionRuns
ORDER BY started_at;

-- Câu 10
SELECT TOP (10) p.store_code, p.name, p.size_value, p.size_unit, p.pack_count, o.sale_price_vnd,
       CAST(o.sale_price_vnd * 100.0 / (p.size_value * ISNULL(p.pack_count, 1)) AS decimal(12,0)) AS price_per_100
FROM dbo.PriceObservations o
JOIN dbo.Products p ON p.product_key = o.product_key
WHERE p.size_value IS NOT NULL
ORDER BY price_per_100;

-- Câu 11
SELECT p.name, o.sale_price_vnd, o.flash_sale_price_vnd,
       o.sale_price_vnd - o.flash_sale_price_vnd AS flash_saving_vnd
FROM dbo.PriceObservations o
JOIN dbo.Products p ON p.product_key = o.product_key
WHERE p.store_code = 'bhx' AND o.flash_sale_price_vnd IS NOT NULL
ORDER BY flash_saving_vnd DESC;

-- Câu 12
SELECT p.store_code,
       CASE WHEN o.sale_price_vnd < 20000  THEN N'Rẻ'
            WHEN o.sale_price_vnd <= 100000 THEN N'Trung bình'
            ELSE N'Cao' END AS price_band,
       COUNT(*) AS observations
FROM dbo.PriceObservations o
JOIN dbo.Products p ON p.product_key = o.product_key
GROUP BY p.store_code,
         CASE WHEN o.sale_price_vnd < 20000  THEN N'Rẻ'
              WHEN o.sale_price_vnd <= 100000 THEN N'Trung bình'
              ELSE N'Cao' END
ORDER BY p.store_code, price_band;

-- Câu 13
SELECT store_code, brand, COUNT(*) AS products
FROM dbo.Products
WHERE brand IS NOT NULL
GROUP BY store_code, brand
HAVING COUNT(*) >= 5
ORDER BY store_code, products DESC;

-- Câu 14
SELECT o.category_slug,
       COUNT(*)                                                         AS observations,
       CAST(AVG(o.sale_price_vnd) AS decimal(12,0))                     AS avg_price,
       CAST(SUM(CASE WHEN o.is_promotion = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS decimal(5,1)) AS promo_pct
FROM dbo.PriceObservations o
GROUP BY o.category_slug
HAVING SUM(CASE WHEN o.is_promotion = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) > 30
ORDER BY promo_pct DESC;

-- Câu 15
SELECT p.store_code, o.dom_price_check, COUNT(*) AS observations
FROM dbo.PriceObservations o
JOIN dbo.Products p ON p.product_key = o.product_key
GROUP BY p.store_code, o.dom_price_check
ORDER BY p.store_code, observations DESC;

-- Câu 16
SELECT brand
FROM dbo.Products
WHERE brand IS NOT NULL
GROUP BY brand
HAVING COUNT(DISTINCT store_code) = 2
ORDER BY brand;

-- Câu 17  (0 dòng = không trùng)
SELECT barcode, COUNT(*) AS products, STRING_AGG(name, N' | ') AS names
FROM dbo.Products
WHERE store_code = 'winmart' AND barcode IS NOT NULL
GROUP BY barcode
HAVING COUNT(*) > 1;

-- Câu 18
SELECT s.store_name, COUNT(o.observation_id) AS observations,
       CAST(AVG(o.sale_price_vnd) AS decimal(12,0)) AS avg_price
FROM dbo.Stores s
LEFT JOIN dbo.Products p          ON p.store_code = s.store_code
LEFT JOIN dbo.PriceObservations o ON o.product_key = p.product_key
GROUP BY s.store_name;

-- Câu 19  (mong đợi 0 dòng vì sản phẩm chỉ được thêm khi có giá)
SELECT p.product_key, p.store_code, p.name
FROM dbo.Products p
LEFT JOIN dbo.PriceObservations o ON o.product_key = p.product_key
WHERE o.observation_id IS NULL;

-- Câu 20  (JOIN 2 lần cùng một bảng với 2 alias khác nhau)
SELECT m.run_id, m.name_similarity, pb.name AS bhx_name, pw.name AS winmart_name, m.reason
FROM dbo.ProductMatches m
JOIN dbo.PriceObservations ob ON ob.observation_id = m.bhx_observation_id
JOIN dbo.PriceObservations ow ON ow.observation_id = m.winmart_observation_id
JOIN dbo.Products pb ON pb.product_key = ob.product_key
JOIN dbo.Products pw ON pw.product_key = ow.product_key
WHERE m.status = 'NEEDS_REVIEW'
ORDER BY m.name_similarity DESC;

-- Câu 21  (run_id dạng run_YYYYMMDD_HHMM nên MAX = lần mới nhất)
SELECT p.name, p.brand, o.sale_price_vnd
FROM dbo.PriceObservations o
JOIN dbo.Products p ON p.product_key = o.product_key
WHERE p.store_code = 'bhx'
  AND o.run_id = (SELECT MAX(run_id) FROM dbo.CollectionRuns)
  AND NOT EXISTS (SELECT 1 FROM dbo.ProductMatches m
                  WHERE m.bhx_observation_id = o.observation_id)
ORDER BY p.brand, p.name;

-- Câu 22
SELECT p.store_code, o.category_slug, p.name, o.sale_price_vnd
FROM dbo.PriceObservations o
JOIN dbo.Products p ON p.product_key = o.product_key
WHERE o.sale_price_vnd > (SELECT AVG(o2.sale_price_vnd)
                          FROM dbo.PriceObservations o2
                          WHERE o2.category_slug = o.category_slug
                            AND o2.run_id = o.run_id)
ORDER BY o.category_slug, o.sale_price_vnd DESC;

-- Câu 23
WITH ranked AS (
    SELECT p.store_code, p.name, o.sale_price_vnd,
           ROW_NUMBER() OVER (PARTITION BY p.store_code ORDER BY o.sale_price_vnd DESC) AS rn
    FROM dbo.PriceObservations o
    JOIN dbo.Products p ON p.product_key = o.product_key
    WHERE o.run_id = (SELECT MAX(run_id) FROM dbo.CollectionRuns)
)
SELECT store_code, rn, name, sale_price_vnd
FROM ranked
WHERE rn <= 3
ORDER BY store_code, rn;

-- Câu 24
WITH by_brand AS (
    SELECT brand,
           COUNT(*)                                          AS pairs,
           SUM(CASE WHEN price_diff_vnd < 0 THEN 1 ELSE 0 END) AS winmart_cheaper,
           SUM(CASE WHEN price_diff_vnd > 0 THEN 1 ELSE 0 END) AS winmart_more_expensive,
           CAST(AVG(price_diff_pct) AS decimal(8,2))         AS avg_diff_pct
    FROM dbo.vw_PriceComparison
    GROUP BY brand
)
SELECT RANK() OVER (ORDER BY avg_diff_pct) AS rank_winmart_cheaper, *
FROM by_brand
ORDER BY rank_winmart_cheaper;

-- Câu 25  (cần ít nhất 2 lần chạy; nếu chỉ có 1 run thì kết quả rỗng)
WITH history AS (
    SELECT p.store_code, p.name, o.run_id, o.collected_at, o.sale_price_vnd,
           LAG(o.sale_price_vnd) OVER (PARTITION BY o.product_key ORDER BY o.collected_at) AS prev_price
    FROM dbo.PriceObservations o
    JOIN dbo.Products p ON p.product_key = o.product_key
)
SELECT store_code, name, run_id, prev_price, sale_price_vnd,
       sale_price_vnd - prev_price AS change_vnd
FROM history
WHERE prev_price IS NOT NULL AND prev_price <> sale_price_vnd
ORDER BY ABS(sale_price_vnd - prev_price) DESC;

-- Câu 26
SELECT p.brand,
       CAST(AVG(CASE WHEN p.store_code = 'bhx'     THEN o.sale_price_vnd END) AS decimal(12,0)) AS avg_bhx,
       CAST(AVG(CASE WHEN p.store_code = 'winmart' THEN o.sale_price_vnd END) AS decimal(12,0)) AS avg_winmart
FROM dbo.PriceObservations o
JOIN dbo.Products p ON p.product_key = o.product_key
WHERE p.brand IS NOT NULL
GROUP BY p.brand
HAVING COUNT(DISTINCT p.store_code) = 2
ORDER BY p.brand;

-- Câu 27  (luôn ROLLBACK → dữ liệu thật không bị thay đổi)
BEGIN TRY
    BEGIN TRANSACTION;
    INSERT INTO dbo.Products (store_code, store_product_code, name, size_value, size_unit,
                              product_url, first_seen_run, last_seen_run)
    VALUES ('bhx', 'TEST-001', N'Sản phẩm thử', 1, 'kg', N'https://example.com', 'test', 'test');
    PRINT N'Insert thành công (không mong đợi!)';
    ROLLBACK TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    PRINT N'Bị chặn: ' + ERROR_MESSAGE();   -- CK_Products_Unit chỉ cho phép 'g' hoặc 'ml'
END CATCH;
