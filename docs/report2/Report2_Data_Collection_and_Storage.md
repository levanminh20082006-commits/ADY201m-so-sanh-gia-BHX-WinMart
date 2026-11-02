# ADY201m – Report 2: Data Collection & Storage

**Topic:** Product Price Analysis and Comparison between Bach Hoa Xanh and WinMart
**Course:** ADY201m – Data Science with Python & SQL, FPT University
**Data collected:** 12 October 2026, 16:22 – 16:43 (Vietnam time, UTC+7)
**Tools:** Python 3.10, Playwright, pandas, pyodbc, SQL Server 2025 Express, pytest, Jupyter

---

## 1. Topic and objectives

Bach Hoa Xanh (BHX) and WinMart are two large supermarket chains in Vietnam. Both publish product prices
on their websites. Our project asks: *for the same product, which store is cheaper, and by how much?*

Report 2 covers the first part of the data science process – **getting good data and storing it**:

1. Collect real product data (name, brand, price, size, package, URL, time) from both websites.
2. Clean and validate the data, and record what was removed and why.
3. Find products that are **really the same** in both stores (product matching).
4. Store raw, clean and matched data so the price history can be analysed later (Report 3).
5. Prove that the numbers are correct (tests, reconciliation, live spot-check).

Goal set before collection: ≥ 500 products per store and ≥ 100 verified matching pairs.
**Result: 1,412 BHX products, 1,955 WinMart products, 139 verified pairs.**

## 2. Data sources

| | Bach Hoa Xanh | WinMart |
|---|---|---|
| Website | https://www.bachhoaxanh.com | https://winmart.vn |
| Pages used | 43 public category pages | 10 public category pages (+1 kept as evidence) |
| Price context | default area, no address chosen (`provinceId=1027`, `storeId=2546`) | online store `storeCode=1535` |
| Barcode | not published | published (EAN-13) |

**Category scope.** We chose 7 groups that both stores sell with the same brands:
milk & dairy, beverages, instant food, seasoning, snacks & confectionery, household cleaning, personal care
(`config/report2_sources.json`). Fresh food (meat, vegetables) was left out because it has no brand and size to match.

**Access rules.** Both `robots.txt` files allow category pages (BHX blocks only cart, account, search, `/sp/*`
and URLs containing `st=`; WinMart blocks only `/_next/`). Copies are saved in `evidence/robots/` and in the run folder.
The code checks every URL against these rules before opening it.

## 3. Collection method

`report2/collect.py` uses **Playwright** (a real Chromium browser, headless):

1. Open a category page like a normal visitor (default browser identity, no login).
2. Scroll down until the list ends. Both sites use *infinite scroll*.
3. Save two kinds of evidence, exactly as received, into `data/raw_py/<run_id>/<store>__<category>.json`:
   - **dom_cards** – the text of every product card shown on the page;
   - **responses** – the product-list JSON that the page itself downloaded while showing the cards.
     We only *listen* to these responses; we never call the websites' APIs ourselves.
4. Wait 5 seconds between pages, 60 s timeout, 1 retry. No CAPTCHA solving or anti-bot bypass.
   A blocked or empty page is recorded as failed.

**Why the JSON responses?** We first read the source of the pages (the earlier JavaScript version of the project and our probes).
The visible cards show name and price, but the JSON the page receives also contains the brand,
WinMart's barcode and selling unit, and BHX's structured size/flavour. We cross-checked every JSON price with the
price on the visible card (section 6).

**Completeness.** WinMart reports how many products a category has (`paging.totalCount`); every completed
WinMart category matched it exactly (e.g. 288/288). BHX's last page is shorter than the page size.
One WinMart page (personal care, 483 products) stopped loading after page 9 of 61 twice; we collected its
4 sub-categories instead and kept the stalled page as evidence.

## 4. Scope and limitations of the data

- One collection run (one point in time). Prices change; more runs are needed for history.
- Prices depend on the store/area: BHX default area, WinMart store 1535.
- BHX's product page can show a different price from its category list (found in our spot-check, section 8).
- BHX has no barcode, so matching uses rules, not codes.

## 5. Dataset structure

Three data layers (full field list in `Data_Dictionary.md`):

| Layer | File / table | One row = |
|---|---|---|
| Raw | `data/raw_py/run_20261012_1622/*.json` (54 files, 15 MB) | one category page (cards + JSON) |
| Clean | `data/processed_py/clean_observations.csv` (3,507 rows) | one product (selling unit) in one store in one run |
| Matched | `data/processed_py/matched_products.csv` (139 rows) | one verified BHX–WinMart pair with price difference |

Main clean fields: store, product code, barcode (WinMart), name, brand, sale price, list price, promotion,
size value + unit (g / ml), pack count, unit label, unit price per kg/L, store/area of the price,
product URL, collected time (+07:00), and `row_id` / `raw_file` that point back to the raw JSON.

## 6. Cleaning and validation

`report2/clean.py` (pandas):

| Step | What we do |
|---|---|
| Structure | Flatten JSON to rows; each row keeps `row_id` = run│store│category│response#│item# |
| Text | Unicode NFC, single spaces; normalised copy without accents for comparing |
| Prices | Convert to integer VND; BHX flash-sale prices (time-limited) kept in a separate column |
| Size | BHX structured spec first, else read from the name; kg→g, L→ml; "1.5L/1.75L" → left empty |
| Pack count | WinMart: from the selling unit (`quantityPerUnit`, e.g. Thùng = 30); BHX: spec or name ("Thùng 48 hộp" → 48); unclear → empty |
| Rules (reject) | missing name, missing product code, missing/unparseable price, price ≤ 0, price outside 1,000–20,000,000 VND, timestamp without +07:00 |
| Duplicates | Same store + product code twice in one run → keep first. The same product in **different runs is kept** (price history). |
| Warnings (keep) | size not found, pack unclear, brand missing, list price < sale price (list price emptied) |
| Cross-check | JSON price vs visible card price |

**Results** (details in `Data_Quality_Report.md`):

| | BHX | WinMart |
|---|---|---|
| Raw rows | 1,514 | 2,266 |
| Rejected (duplicates / combos) | 102 | 171 |
| Clean rows | 1,412 | 2,095 (1,955 products) |
| JSON price = visible card price | 1,412 / 1,412 (46 via flash price) | 0 mismatches (201 rows have no card) |

No missing value was filled with a guess.

## 7. Product matching

`report2/matching.py` decides, for every BHX product, whether WinMart sells **exactly the same product**.
We never match on "similar name" alone. Rules:

1. **Same brand** – equal brand, a documented alias (e.g. *Ottogi* = *OTOKI*), or the brand written in the other
   store's product name (BHX brand *Hảo Hảo*, WinMart name "Mì **Hảo Hảo** …", brand ACECOOK).
2. **Same size per unit** (after converting units) **and same pack count**.
3. **No variant conflict** – flavour, sugar level and product line words must agree
   (*dâu* ≠ *cam*, *ít đường* ≠ *có đường*, *Canxi* ≠ *nguyên chất*, *tiệt trùng* ≠ *thanh trùng*).
4. **Name similarity** (word overlap, Jaccard) ≥ 0.5, and neither name has extra distinctive words
   (e.g. *Classic* vs *Gentleman*) or another brand's name.
5. **One-to-one** – a WinMart product can be used once; ties go to review.

| Status | Meaning | Count |
|---|---|---|
| MATCHED | all rules pass | **139** |
| NEEDS_REVIEW | possible, but some evidence is weak – not used in the comparison | 119 |
| NOT_MATCHED | no WinMart product passes rules 1–3 | 1,154 |

Every MATCHED pair has both URLs, both collection times and the reason. Example rows:

| BHX product (price) | WinMart product [unit] (price) | WinMart − BHX |
|---|---|---|
| Sữa tươi Vinamilk ít đường 1 lít (41,000) | Sữa tươi tiệt trùng Vinamilk ít đường hộp 1 lít [Hộp] (38,300) | −2,700 (−6.59%) |
| Mì Hảo Hảo sườn heo tỏi phi gói 73g (4,600) | … Hảo Hảo 73g [Gói] (4,700) | +100 (+2.17%) |
| Lốc 4 hộp sữa chua YoMost dâu 170ml (29,500) | Sữa chua uống vị dâu YoMost lốc 4 hộp x 170ml [Gói (Lốc) 4] (30,600) | +1,100 (+3.73%) |
| Tương ớt Chinsu 250g (19,500) | Tương ớt Chin-su 250g [Chai] (18,800) | −700 (−3.59%) |
| Dầu đậu nành Simply 1 lít (60,000) | Dầu đậu nành Simply chai 1 lít [Chai] (70,800) | +10,800 (+18.00%) |

**How the rules were tested.** All MATCHED pairs were read by hand during development. This found real errors
in earlier versions (e.g. a WinMart *carton* price compared with a BHX *single pack*, *Coca giảm đường* matched with
regular Coca), and each error became a new rule plus a unit test.

## 8. Price difference dataset

For each MATCHED pair:

- `Price Difference = WinMart price − BHX price`
- `Price Difference (%) = Price Difference / BHX price × 100`

Positive → WinMart is more expensive; negative → WinMart is cheaper. Both prices must be valid and collected
at most 3 hours apart; in our run the gap is 0.6–3.4 **minutes**, so all 139 pairs are comparable.

Descriptive summary only (analysis belongs to Report 3): WinMart cheaper in 65 pairs, more expensive in 65,
same price in 9; median difference 0.00%, range −32.3% to +48.8%.

## 9. Storage

**Files:** raw JSON (evidence), CSV (clean, rejected, match results, matched pairs, UTF-8 with BOM for Excel).

**SQL Server:** database `ADY201m_Report2` on `localhost\SQLEXPRESS` (a new database created only for this project,
with the owner's permission; Windows Authentication, no password in code). Schema in `sql/01_schema.sql`:

| Table | Key / constraints |
|---|---|
| `Stores` | PK `store_code` |
| `CollectionRuns` | PK `run_id`; CHECK pages |
| `Products` | PK identity; **UNIQUE (store_code, store_product_code)**; CHECK size unit, pack > 0 |
| `PriceObservations` | PK `observation_id`; **UNIQUE (run_id, product_key)**; CHECK price > 0; CHECK list ≥ sale; FKs |
| `ProductMatches` | CHECK status; UNIQUE per run on each side (one-to-one) |
| `vw_PriceComparison` | view: MATCHED + comparable pairs |

One price per product per run → each new run adds a new row = **price history**. Times are `datetimeoffset` (+07:00).
`report2/storage.py` writes one run in **one transaction** (all or nothing) and skips rows that already exist,
so re-running does not create duplicates. A name guard refuses any database not named `ADY201m_Report2*`.

## 10. Verification results

| Check | Result |
|---|---|
| Automated tests (`pytest`, 51 tests incl. SQL tests on the separate `ADY201m_Report2_Test` database) | **51 passed** |
| Reconciliation JSON → CSV → SQL (6 checks) | **6 / 6 passed** (3,780 raw = 3,507 clean + 273 rejected; 3,507 rows in SQL; 139 + 119 matches in SQL) |
| Load the same run twice | 2nd load: **0 inserted**, 3,507 skipped |
| SQL duplicate queries | 0 rows |
| Live spot-check of 12 MATCHED pairs (~45 min later) | titles 12/12 both stores; exact price WinMart 12/12, BHX 7/12 |

The 5 BHX price differences in the spot-check were checked again: the BHX **category data still showed the stored
prices**, while the **product pages** showed a slightly different price. The collected data is correct; BHX shows
two prices in two places. We report this as a limitation instead of hiding it.

## 11. Limitations

1. Only one collection run so far.
2. Prices are for one BHX area and one WinMart store.
3. BHX product page price can differ from its category list price.
4. No barcode at BHX; 119 possible pairs still need a human check.
5. Size and pack are read by rules; 188 rows have no size and 193 an unclear pack count.
6. Only 7 category groups; matched pairs are mostly food (instant food 52, seasoning 31, dairy 23).
7. If the websites change their pages or JSON, the collector must be updated.

## 12. Next steps (Report 3)

- Run the collector several times (different days and hours) to build price history.
- Review the 119 NEEDS_REVIEW pairs by hand and add confirmed ones.
- Analyse price differences by category, brand and time; check whether promotions explain the differences.

---

### Appendix – how to reproduce

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = "0"; $py = ".\.venv\Scripts\python.exe"
& $py -m report2.collect; & $py -m report2.clean; & $py -m report2.matching
& $py -m report2.storage; & $py -m report2.reconcile; & $py -m report2.verify_samples --n 12
```
Notebook: `notebooks/Report2_Data_Collection_Storage.ipynb`. SQL demo: `sql/02_demo_queries.sql`.
