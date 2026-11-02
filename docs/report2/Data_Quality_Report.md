# Data Quality Report – ADY201m Report 2

Run analysed: **`run_20261012_1622`** (12 Oct 2026, 16:22:03 → 16:43:23, Vietnam time UTC+7).
All numbers come from `reports_py/data_quality_report.json`, `reports_py/matching_summary.json`,
`reports_py/reconciliation_run_20261012_1622.json` and `reports_py/sample_verification.json`
(produced by the code; re-run `python -m report2.clean` / `matching` / `reconcile` to regenerate).

---

## 1. Collection completeness

| Item | Value |
|---|---|
| Category pages planned (`config/report2_sources.json`) | 50 at start (43 BHX + 7 WinMart); 53 after the change below (43 BHX + 10 WinMart) |
| Page records in the run | 54 (the 50 original pages + 4 WinMart sub-categories added during the run) |
| Pages with status `ok` | 54 / 54 |
| Pages where the end of the list was confirmed | 53 / 54 |
| Page not confirmed | `winmart/cham-soc-ca-nhan--c11` – the site stopped loading after page 9 of 61 (twice). Its 4 sub-categories (oral care, hair, skin/body, tissue) were collected instead, all complete. The stalled page is kept as evidence. |
| WinMart completeness check | Every complete WinMart category: unique products collected = `paging.totalCount` reported by the site (e.g. 288/288, 280/280, 427/427) |
| BHX completeness check | Last list page returned fewer items than the page size (BHX does not publish a total) |

## 2. Rows through the pipeline

| Step | BHX | WinMart | Total |
|---|---|---|---|
| Raw rows flattened from JSON | 1,514 | 2,266 | 3,780 |
| Rejected | 102 | 171 | 273 |
| **Clean rows** | **1,412** | **2,095** | **3,507** |
| Distinct products in clean data | 1,412 | 1,955 | 3,367 |

WinMart has more clean rows than products because one product can be sold in several **selling units**
(e.g. *Gói* = 1 pack and *Thùng* = 30 packs), each with its own SKU and price. 140 rows are such extra units.

### Rejected rows by reason

| Reason | Rows | Explanation |
|---|---|---|
| `duplicate_in_run` | 200 (BHX 29, WinMart 171) | Same product seen twice in one run, e.g. listed on a parent and a child category page. First occurrence kept. |
| `missing_product_code` | 73 (BHX) | BHX **combo bundles** ("Dầu gội 340ml và kem xả 327ml Dove", "Combo gia vị…"). They have no product code, are not shown as cards on the page and cannot be compared with single products. |
| missing name / price, price ≤ 0, price out of range, bad timestamp | 0 | Rules were applied; no row failed them. |

Exact duplicate raw rows (all fields identical): **102** – all inside the `duplicate_in_run` group.

## 3. Missing values

### Raw rows (% missing)

| Field | BHX | WinMart | Note |
|---|---|---|---|
| name, brand, sale price, list price, URL, collected_at | 0 | 0 | |
| product_code | 4.82 | 0 | = the 73 BHX combos |
| barcode | **100** | 0 | BHX does not publish barcodes |
| structured size (`spec_size`) | 94.19 | 100 | BHX gives it for few categories; WinMart never. Size is then read from the name. |

### Clean rows (% missing)

| Field | BHX | WinMart |
|---|---|---|
| brand | 0.07 | 0.57 |
| list (original) price | 0.00 | 0.10 |
| size (g / ml) | 1.70 | 7.83 |
| pack count | 4.46 | 6.21 |
| barcode | 100 | 0 |
| unit price (VND per kg or L) | 6.09 | 13.70 |

Missing values were **not filled**. A row without size or pack count is kept but cannot be matched.

## 4. Validation and warnings (rows kept)

| Warning | Rows | Meaning |
|---|---|---|
| `pack_count_unclear` | 193 | Multipack word (thùng, lốc…) without a clear number |
| `size_not_found` | 188 | No weight/volume in name or spec (e.g. tissues, toothbrushes) |
| `pack_count_conflict_name_vs_unit` | 32 | WinMart name says one count, selling unit another → left empty |
| `brand_missing` | 13 | No brand from the store |
| `list_price_below_sale_price` | 2 | Inconsistent original price → original price emptied |

### Price cross-check: JSON price vs price visible on the product card

| Store | Result |
|---|---|
| BHX | 1,366 exact match + 46 match the **flash-sale** price shown on the card (we keep the regular price; flash price stored separately) → **1,412 / 1,412 explained** |
| WinMart | 1,890 exact match + 4 match a **per-kg** item shown as a 0.5 kg price + 201 not visible (140 = extra selling units that are not on the card; 61 = delivered in JSON but not rendered as cards) → **0 mismatches** |

## 5. Price overview (clean data)

| Store | Rows | Min | Max | Mean | On promotion |
|---|---|---|---|---|---|
| BHX | 1,412 | 3,600 | 1,521,000 | 88,380 | 347 (24.6%) |
| WinMart | 2,095 | 2,600 | 1,226,000 | 82,631 | 234 (11.2%) |

Price context: BHX `provinceId=1027`, `storeId=2546` (default area, no address chosen). WinMart `storeCode=1535`, `storeGroupCode=1998`.

## 6. Product matching quality

| Result (one row per BHX product) | Count |
|---|---|
| **MATCHED** | **139** |
| NEEDS_REVIEW | 119 |
| NOT_MATCHED | 1,154 |
| WinMart rows without a pair | 1,837 |

| NOT_MATCHED reason | Count |
|---|---|
| No WinMart product with the same brand, size and pack | 873 |
| BHX size or pack count missing | 86 |
| Variant conflict (flavour / sugar / product line) | 85 |
| Name similarity < 0.3 | 76 |
| Best candidate already used by another BHX product | 34 |

| NEEDS_REVIEW reason | Count |
|---|---|
| Name similarity 0.3 – 0.5 | 31 |
| Variant word on one side only | 26 |
| One name has 2+ extra distinctive words | 24 |
| Several equally good candidates | 19 |
| Each name has a distinctive word the other lacks | 16 |
| Name contains another brand (e.g. "Reeva", "Purité") | 3 |

Matched pairs by group: instant food 52, seasoning 31, milk & dairy 23, beverages 15, snacks 11, household 4, personal care 3.
Brand evidence: 135 equal brand, 4 brand written in the other store's product name.
Time gap between the two prices of a pair: 0.6 – 3.4 minutes (limit 3 hours) → all 139 pairs are price-comparable.

**Manual review:** all MATCHED pairs were read one by one during development. This review found and fixed
false matches (e.g. *Fami Canxi* vs *Fami nguyên chất*, *Coca giảm đường* vs regular, carton price vs single item),
which is why the rules in `report2/matching.py` became stricter.

## 7. Storage verification (SQL Server `ADY201m_Report2`)

| Check (`reports_py/reconciliation_run_20261012_1622.json`) | Result |
|---|---|
| JSON rows = flat CSV rows (3,780) | ✅ |
| Raw rows = clean + rejected | ✅ |
| Clean CSV rows = SQL `PriceObservations` (BHX 1,412 / WinMart 2,095) | ✅ |
| MATCHED in CSV = in SQL (139) | ✅ |
| NEEDS_REVIEW in CSV = in SQL (119) | ✅ |
| No duplicate (run, product) in SQL | ✅ |
| Second load of the same run | 0 rows inserted, 3,507 skipped (`evidence/sql/storage_load_*.txt`) |

## 8. Live spot-check (`reports_py/sample_verification.json`)

12 random MATCHED pairs (seed 42) were opened again on both sites ~45 minutes after collection (17:08–17:12).

| Check | BHX | WinMart |
|---|---|---|
| Page title describes the same product | 12 / 12 | 12 / 12 |
| Stored price = product's current price on its page | **7 / 12** | **12 / 12** |

The 5 BHX differences (37,500→35,500; 129,000→126,000; 11,200→11,000; 9,100→9,300; 4,700→4,600) were investigated:
re-opening the **BHX category pages at 17:12–17:13 showed exactly the stored prices** (store 2546) for the 4 items
re-checked (`evidence/bhx_category_vs_product_page_price_check.txt`). So the collected data is correct, but **BHX's product
page can show a different price than its category list** for the same product. This is a known limitation (section 9).

## 9. Known limitations

1. **One snapshot** – one run on 12 Oct 2026. History needs more runs (the schema already supports it).
2. **Price context** – BHX default area (no address), WinMart store 1535; other areas/stores may differ.
3. **BHX category vs product page price** – may differ (see §8). We consistently use category-page prices for both stores.
4. **No barcode at BHX** – matching relies on rules (brand, size, pack, variant, name); 119 possible pairs need a human check.
5. **BHX naming inconsistency** – e.g. listing "Sữa dinh dưỡng Vinamilk 220ml" but product page title "Sữa tươi…"; the listing name, `fullName` and URL (`stt-…`, sữa tiệt trùng) agree, so the match was kept.
6. **Rule-based parsing** of size and pack count; 188 rows without size and 193 with unclear pack count cannot be matched.
7. **Coverage** – 7 category groups; fresh food without brands was not included.
