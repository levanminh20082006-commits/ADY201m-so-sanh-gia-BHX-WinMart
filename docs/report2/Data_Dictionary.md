# Data Dictionary – ADY201m Report 2

Project: *Product Price Analysis and Comparison between Bach Hoa Xanh and WinMart*.
Three data layers: **Raw (JSON)** → **Clean (CSV)** → **Matched (CSV)**, plus **SQL Server** tables.

Empty value = the source did not provide it, or we could not read it with certainty. We never fill it with a guess.

---

## 1. Raw data – `data/raw_py/<run_id>/<store>__<category>.json`

One file per category page. Kept exactly as received (evidence).

| Field | Type | Meaning |
|---|---|---|
| `run_id` | text | Collection run, e.g. `run_20261012_1625` |
| `store` | text | `bhx` or `winmart` |
| `group` | text | Category group from `config/report2_sources.json` (e.g. `milk_dairy`) |
| `category_slug` | text | Category part of the URL (e.g. `sua-tuoi`, `sua-cac-loai--c08`) |
| `source_url` | text | Category page opened |
| `requested_at` / `collected_at` | datetime +07:00 | When the page was opened / when cards were read (Vietnam time) |
| `status` | text | `ok`, `no_items`, `failed` |
| `error` | text | Error message if failed |
| `http_status`, `page_title`, `final_url` | – | Page load evidence |
| `scroll_card_counts` | list | Number of cards after each scroll (shows infinite-scroll loading) |
| `end_reached` | bool | The site's last page was reached (WinMart: page = totalPages; BHX: last page smaller than page size) |
| `site_total_count` | int | WinMart only: total products the site says the category has |
| `responses[]` | list | Product-list JSON the page downloaded: `url`, `status`, `method`, `request_body`, `received_at`, `body` |
| `dom_cards[]` | list | Visible product cards: `product_code`, `url`, `name`, `price_text`, `original_price_text`, `discount_badge`, `card_text` |

Also in each run folder: `manifest.json` (all pages + settings + start/finish time) and `robots_<store>.txt`.

---

## 2. Flattened raw rows – `data/processed_py/raw_products_flat.csv`

One row per product per response, before any filtering. Same fields as the clean file's *raw* columns (below) plus `response_index`, `item_index`, `in_dom`, `dom_name`, `dom_prices`, `dom_promo_line`.

---

## 3. Clean data – `data/processed_py/clean_observations.csv`

One row = **one product, in one store, in one run** (price observation). Valid and de-duplicated.

| Field | Type | Source BHX | Source WinMart | Meaning |
|---|---|---|---|---|
| `observation_id` | text(20) | – | – | SHA-1 of `run_id|store|product_code` (primary key) |
| `run_id` | text | – | – | Collection run |
| `collected_at` | datetime +07:00 | – | – | When the price was read (Vietnam time, UTC+7, no DST) |
| `store` | text | – | – | `bhx` / `winmart` |
| `group`, `category_slug` | text | – | – | Category the row was collected from |
| `site_category` | text | `category.name` | `categoryName` | Category name used by the site |
| `product_code` | text | `productCode` | `uoms[].sku` (e.g. `10007893G1`) | Store's code for this product **and selling unit** (not shared between stores) |
| `site_product_id` | text | `id` | `id` | Internal website id |
| `site_item_no` | text | – | `itemNo` | WinMart product number (same for all selling units of one product) |
| `uom_is_primary` | bool | always true | unit shown on the card | WinMart: false for extra selling units (e.g. *Gói* of a product shown as *Thùng*) |
| `barcode` | text | **not published** | `barcode` | EAN-13 barcode (WinMart only) |
| `name_clean` | text | `name` | `name` | Product name, Unicode NFC, single spaces, accents kept |
| `full_name` | text | `fullName` | `description` | Longer name from the site |
| `name_normalized` | text | – | – | Lowercase, no accents (đ→d), only letters/digits – for comparing |
| `brand` | text | `brandName` | `brandName` | Brand as written by the store |
| `brand_key` | text | – | – | Brand lowercase, no accents/spaces (`TH true MILK` → `thtruemilk`) |
| `sale_price_vnd` | int | `productPrices[0].price` | `salePrice` | **Actual selling price** (VND) used for comparison |
| `list_price_vnd` | int | `productPrices[0].sysPrice` | `price` | Original/list price; emptied if lower than sale price (inconsistent) |
| `is_promotion` | bool | – | – | `list_price_vnd > sale_price_vnd` |
| `discount_pct` | float | – | – | `(1 − sale/list) × 100`, 0 if no promotion |
| `promotion_text` | text | `promotionText` | `promotionType` | Promotion description / code |
| `flash_sale_price_vnd` | int | `lstCampaingInfo[0].productPrice.price` | – | BHX time-limited flash price (not used for comparison) |
| `flash_sale_start`, `flash_sale_end` | datetime | `startTime`, `dueTime` | – | Flash sale time window |
| `dom_promo_line` | text | card text | card text | Promo line shown on the card ("Mua 2 … với giá …") |
| `size_value` | float | spec *Dung tích / Khối lượng*, else name | name | Weight or volume of **one unit**, in base unit |
| `size_unit` | text | – | – | `g` or `ml` (kg×1000 → g, L×1000 → ml) |
| `size_source` | text | – | – | `spec`, `name` or `full_name` |
| `pack_count` | int | spec *Số lượng hoặc đóng gói*, else name | name | Units sold together (`Thùng 48 hộp` → 48). 1 = single item. Empty = multipack with unknown count |
| `pack_source` | text | – | – | `spec` or `name` |
| `unit_label` | text | `unit` | `uomName` | Selling unit (`Hộp`, `Lốc`, `Thùng`, `Gói`…) |
| `spec_flavor` | text | spec *Hương vị* | – | Flavour (BHX only) |
| `total_quantity` | float | – | – | `size_value × pack_count` (g or ml) |
| `unit_price_vnd_per_kg_or_l` | float | – | – | `sale_price / total_quantity × 1000` |
| `can_buy` | bool | `isCanBuy` | `quantity > 0` | Available to buy at collection time |
| `stock_qty` | float | – | `quantity` | Stock quantity shown by WinMart |
| `price_store_id` | text | `storeId` (2546) | `storeCode` (1535) | Store the price belongs to |
| `price_area` | text | `provinceId=1027` | `storeGroupCode=1998` | Area / store group of the price |
| `product_url` | text | – | – | Public product page |
| `source_url` | text | – | – | Category page it was found on |
| `dom_price_check` | text | – | – | JSON price vs visible card: `match`, `match_flash_sale`, `mismatch`, `not_visible` |
| `warnings` | text | – | – | Kept-row warnings: `size_not_found`, `pack_count_unclear`, `brand_missing`, `list_price_below_sale_price`, `dom_price_mismatch`, `not_buyable_now` |
| `raw_file` | text | – | – | Raw JSON file of this row |
| `row_id` | text | – | – | `run|store|category|r<response#>|i<item#>` – exact position in the raw file |

### Rejected rows – `data/processed_py/rejected_rows.csv`
`row_id`, `run_id`, `store`, `category_slug`, `product_code`, `name`, `sale_price_raw`, `collected_at`, `raw_file`, and
`reject_reason`, one of:

| reject_reason | Rule |
|---|---|
| `missing_name` | No product name |
| `missing_product_code` | No store product code |
| `missing_or_unparseable_price` | No price, or text that is not a number |
| `price_not_positive` | Price ≤ 0 |
| `price_out_of_range` | Price < 1,000 or > 20,000,000 VND (treated as a reading error) |
| `invalid_or_naive_timestamp` | Time missing or without the +07:00 offset |
| `duplicate_in_run` | Same store + product code already kept in this run (e.g. product listed in 2 categories) |

---

## 4. Matching – `data/processed_py/match_results.csv` and `matched_products.csv`

`match_results.csv`: one row per BHX product of the run, with its best WinMart candidate.
`matched_products.csv`: only `status = MATCHED`, plus price-difference columns.

| Field | Meaning |
|---|---|
| `status` | `MATCHED` (verified by rules), `NEEDS_REVIEW` (possible, not used), `NOT_MATCHED` |
| `reason` | Why: e.g. `brand_equal+size+pack+variant+name`, `variant_conflict […] vs […]`, `medium_name_similarity`, `ambiguous: …`, `no_winmart_product_with_same_brand_size_and_pack` |
| `name_similarity` | Jaccard word overlap of the two names (brand, sizes and packaging words removed) |
| `match_brand`, `brand`, `size_value`, `size_unit`, `pack_count` | Values that were required to be equal |
| `bhx_variants`, `winmart_variants` | Flavour/sugar/product-line words found in each name |
| `bhx_*`, `winmart_*` | `observation_id`, `product_code`, `name`, `price_vnd`, `list_price_vnd`, `url`, `collected_at` (+ `winmart_barcode`, `winmart_brand`) |
| `price_diff_vnd` | **WinMart price − BHX price**. Positive = WinMart more expensive; negative = WinMart cheaper |
| `price_diff_pct` | `price_diff_vnd / BHX price × 100` |
| `time_gap_minutes` | Minutes between the two prices were collected |
| `price_comparable` | Both prices valid and collected ≤ 3 hours apart |
| `cheaper_store` | `bhx`, `winmart` or `same_price` |

---

## 5. SQL Server – database `ADY201m_Report2`

| Table | Primary key | Main constraints | Content |
|---|---|---|---|
| `dbo.Stores` | `store_code` | – | 2 rows: bhx, winmart |
| `dbo.CollectionRuns` | `run_id` | `CHECK pages_ok BETWEEN 0 AND pages_total` | One row per collection run |
| `dbo.Products` | `product_key` (identity) | `UNIQUE (store_code, store_product_code)`, FK Stores, `CHECK size_unit IN ('g','ml')`, `CHECK pack_count > 0` | One row per store product |
| `dbo.PriceObservations` | `observation_id` | `UNIQUE (run_id, product_key)`, FK Runs/Products, `CHECK sale_price_vnd > 0`, `CHECK list_price_vnd >= sale_price_vnd` | One price per product per run = **price history** |
| `dbo.ProductMatches` | `match_id` (identity) | `CHECK status IN ('MATCHED','NEEDS_REVIEW')`, `UNIQUE (run_id, bhx_observation_id)`, `UNIQUE (run_id, winmart_observation_id)` (one-to-one) | Matched and to-review pairs |
| `dbo.vw_PriceComparison` (view) | – | only `MATCHED` and `price_comparable = 1` | Main comparison table |

Times are stored as `datetimeoffset(0)` so the +07:00 offset is kept.
