"""Builds notebooks/Report2_Data_Collection_Storage.ipynb (run: python notebooks/build_notebook.py).

The notebook only READS the files produced by the pipeline and runs SELECT queries on
ADY201m_Report2, so executing it never changes data.
"""
from pathlib import Path

import nbformat as nbf

cells = []
md = lambda text: cells.append(nbf.v4.new_markdown_cell(text.strip()))
code = lambda text: cells.append(nbf.v4.new_code_cell(text.strip()))

md("""
# ADY201m – Report 2: Data Collection & Storage
**Topic:** Product Price Analysis and Comparison between Bach Hoa Xanh (BHX) and WinMart

This notebook shows how the data goes **from the websites → raw JSON → clean CSV → matched pairs → SQL Server**.
Every number below is computed from the real files in this project; nothing is typed by hand.

Run the cells from top to bottom (Kernel → Restart & Run All).
""")

md("""
## 1. Project objective
- Collect **real** product prices from the public websites of BHX and WinMart.
- Clean and validate the data, keeping a trace back to the raw source.
- Find products that are **truly the same** in both stores (same brand, size, pack, variant).
- Store everything in SQL Server so price history can be analysed in Report 3.
""")

code("""
import json, sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
sys.path.insert(0, str(ROOT))
from report2 import settings, storage

pd.set_option('display.max_colwidth', 60)
PROCESSED, REPORTS, RAW = settings.PROCESSED_DIR, settings.REPORTS_DIR, settings.RAW_DIR
RUN_ID = sorted(p.name for p in RAW.glob('run_*') if (p / 'manifest.json').exists())[-1]
print('Project folder:', ROOT)
print('Run analysed  :', RUN_ID)
""")

md("""
## 2. Data sources
| Store | Website | Price context |
|---|---|---|
| Bach Hoa Xanh | https://www.bachhoaxanh.com | default delivery area (no address chosen): `provinceId=1027`, `storeId=2546` |
| WinMart | https://winmart.vn | online store `storeCode=1535` (`storeGroupCode=1998`) |

Prices depend on the store/area and the time. We record both for every price.

**Category scope** (`config/report2_sources.json`): 7 groups that both stores sell — milk & dairy, beverages,
instant food, seasoning, snacks & confectionery, household cleaning, personal care.
""")

code("""
sources = json.loads(settings.SOURCES_FILE.read_text(encoding='utf-8'))
pd.DataFrame([{'group': g['group'], 'BHX categories': ', '.join(g['bhx']), 'WinMart categories': ', '.join(g['winmart'])}
              for g in sources['groups']])
""")

md("""
## 3. Collection method (Python + Playwright)
1. Check `robots.txt` – category pages are allowed on both sites (copies saved in `evidence/robots/` and in each run folder).
2. Open each category page in Chromium like a normal visitor, then scroll until the list ends.
3. Save two kinds of evidence **exactly as received**:
   - `dom_cards`: the text of each product card visible on the page,
   - `responses`: the product-list JSON the page itself downloaded while rendering (we only *listen*; we never call the API ourselves).
4. Wait 5 seconds between pages, 60 s timeout, 1 retry. No login, no CAPTCHA solving, no anti-bot bypass.

How do we know a category is complete? WinMart reports `totalCount`; BHX's last page returns fewer items than the page size.
""")

code("""
manifest = json.loads((RAW / RUN_ID / 'manifest.json').read_text(encoding='utf-8'))
pages = pd.DataFrame(manifest['pages'])
print('Started:', manifest['started_at'], ' Finished:', manifest['finished_at'])
print(pages['status'].value_counts().to_string())
pages[['store', 'group', 'category_slug', 'status', 'dom_cards', 'responses', 'end_reached', 'site_total_count']]
""")

md("""
## 4. Python libraries
| Library | Used for |
|---|---|
| `playwright` | open the web pages and read product cards / JSON |
| `pandas` | cleaning, validation, matching, CSV |
| `pyodbc` | connect to SQL Server (Windows Authentication, no password in code) |
| `re`, `unicodedata` | parse prices, sizes and Vietnamese text |
| `pytest` | automatic tests |
""")

md("## 5. Raw data preview\nOne raw file = one category page. Here is one product from BHX and one from WinMart, as saved.")

code("""
raw_bhx = json.loads((RAW / RUN_ID / 'bhx__sua-tuoi.json').read_text(encoding='utf-8'))
p = raw_bhx['responses'][0]['body']['data']['products'][0]
print('BHX keys:', list(p)[:25])
print({k: p[k] for k in ('productCode', 'name', 'brandName', 'unit', 'exchangeQuantity')}, p['productPrices'][0]['price'])
print('Visible card text:', raw_bhx['dom_cards'][0]['card_text'].replace(chr(10), ' | ')[:200])
""")

code("""
raw_wm = json.loads((RAW / RUN_ID / 'winmart__sua-cac-loai--c08.json').read_text(encoding='utf-8'))
i = raw_wm['responses'][0]['body']['data']['items'][0]
print({k: i[k] for k in ('itemNo', 'barcode', 'name', 'brandName', 'uomName', 'price', 'salePrice')})
print('Paging info:', raw_wm['responses'][-1]['body'].get('paging'))
""")

md("## 6. Dataset structure\nThe raw JSON is flattened to one row per product per page (`raw_products_flat.csv`).")

code("""
flat = pd.read_csv(PROCESSED / 'raw_products_flat.csv', dtype=str)
flat = flat[flat['run_id'] == RUN_ID]
print('Raw rows:', len(flat)); print(flat['store'].value_counts().to_string())
flat[['row_id', 'store', 'product_code', 'name', 'brand_raw', 'sale_price_raw', 'list_price_raw', 'unit_label']].head()
""")

md("""
## 7. Data cleaning
- Text: Unicode NFC, extra spaces removed; a normalised copy without accents for comparing.
- Prices: converted to integers in VND.
- Size: BHX structured spec first (e.g. *Dung tích: 180ml*), otherwise read from the name; kg→g and L→ml.
- Pack count: e.g. *Thùng 48 hộp* → 48. Unclear multipacks stay empty (**we do not guess**).
- BHX flash-sale prices (time-limited) are kept in a separate column; the regular shelf price is used for comparison.
- Missing values stay missing.
""")

code("""
clean = pd.read_csv(PROCESSED / 'clean_observations.csv', dtype={'product_code': str, 'barcode': str})
clean = clean[clean['run_id'] == RUN_ID]
clean[['store', 'name_clean', 'brand', 'sale_price_vnd', 'list_price_vnd', 'size_value', 'size_unit',
       'pack_count', 'unit_price_vnd_per_kg_or_l', 'collected_at']].sample(8, random_state=1)
""")

md("## 8. Data validation summary")

code("""
quality = json.loads((REPORTS / 'data_quality_report.json').read_text(encoding='utf-8'))
rows = quality['rows']
summary = pd.DataFrame({'raw rows': rows['raw_by_store'], 'clean rows': rows['clean_by_store'],
                        'rejected rows': rows['rejected_by_store'],
                        'distinct products': quality['distinct_products_by_store']}).T
display(summary)
print('Rejected by reason:', rows['rejected_by_reason'])
print('Visible card price vs JSON price:', quality['dom_price_check_clean'])
""")

code("""
missing = pd.DataFrame(quality['missing_pct_clean'])
display(missing)
missing.plot.bar(figsize=(8, 3), title='Missing values in clean data (%)'); plt.ylabel('%'); plt.tight_layout(); plt.show()
""")

md("""
## 9. Product matching (BHX ↔ WinMart)
A pair is only considered if **brand, size per unit and pack count are equal**. Then:
- flavour / sugar / product-line words must not conflict (e.g. *dâu* vs *socola* → different product),
- name similarity (word overlap) ≥ 0.5 for **MATCHED**; 0.3–0.5 or a variant word on only one side → **NEEDS_REVIEW**,
- one WinMart product can be matched to only one BHX product; ties → NEEDS_REVIEW.

Only **MATCHED** pairs go into the comparison table. NEEDS_REVIEW is kept for manual checking.
""")

code("""
match_info = json.loads((REPORTS / 'matching_summary.json').read_text(encoding='utf-8'))
print('Status counts:', match_info['status_counts'])
print('Price-comparable pairs:', match_info['price_comparable_pairs'])
pd.Series(match_info['not_matched_reasons']).head(10).to_frame('NOT_MATCHED reasons')
""")

code("""
matched = pd.read_csv(PROCESSED / 'matched_products.csv')
matched[['brand', 'bhx_name', 'winmart_name', 'bhx_price_vnd', 'winmart_price_vnd',
         'price_diff_vnd', 'price_diff_pct', 'name_similarity']].sample(10, random_state=2)
""")

md("""
## 10. Price difference preparation
`Price Difference = WinMart price − BHX price`, `Price Difference (%) = Difference / BHX price × 100`.
Positive → WinMart is more expensive; negative → WinMart is cheaper. (Descriptive only – analysis is Report 3.)
""")

code("""
comp = matched[matched['price_comparable']]
print(comp['cheaper_store'].value_counts().to_string())
comp['price_diff_pct'].plot.hist(bins=30, figsize=(7, 3), title='Price difference % (WinMart vs BHX), matched pairs')
plt.xlabel('%'); plt.tight_layout(); plt.show()
""")

md("## 11. Storage verification (SQL Server `ADY201m_Report2`)\nThe notebook only runs `SELECT` queries here.")

code("""
conn = storage.connect()
q = lambda sql, *a: pd.read_sql(sql, conn, params=list(a) or None)
display(q('''SELECT 'Products' AS table_name, COUNT(*) AS n FROM dbo.Products
             UNION ALL SELECT 'PriceObservations', COUNT(*) FROM dbo.PriceObservations
             UNION ALL SELECT 'ProductMatches', COUNT(*) FROM dbo.ProductMatches'''))
rec = json.loads((REPORTS / f'reconciliation_{RUN_ID}.json').read_text(encoding='utf-8'))
pd.Series(rec['checks']).to_frame('passed')
""")

md("""
### Live spot-check of matched pairs (`python -m report2.verify_samples`)
12 random MATCHED pairs were opened again on both websites. WinMart: the product page price (after choosing the
same selling unit) is compared exactly. BHX: the price in the page's schema.org Product data is compared exactly.
""")

code("""
ver = json.loads((REPORTS / 'sample_verification.json').read_text(encoding='utf-8'))
print(ver['summary'])
pd.DataFrame([{'store': side, 'name': p[side + '_name'][:50], 'stored': p[side]['stored_price'],
               'page now': p[side].get('page_main_price'), 'exact': p[side].get('price_match'),
               'checked_at': p[side]['checked_at']} for p in ver['pairs'] for side in ('bhx', 'winmart')])
""")

md("## 12. SQL query examples (same as `sql/02_demo_queries.sql`)")

code("""
q('''SELECT p.store_code, COUNT(*) AS observations, MIN(o.sale_price_vnd) AS min_price,
            MAX(o.sale_price_vnd) AS max_price, CAST(AVG(o.sale_price_vnd) AS decimal(12,0)) AS avg_price
     FROM dbo.PriceObservations o JOIN dbo.Products p ON p.product_key = o.product_key
     WHERE o.run_id = ? GROUP BY p.store_code''', RUN_ID)
""")

code("""
q('''SELECT run_id, product_key, COUNT(*) AS times FROM dbo.PriceObservations
     GROUP BY run_id, product_key HAVING COUNT(*) > 1''')   # expected: empty = no duplicates
""")

code("""
q('''SELECT TOP (10) brand, bhx_name, winmart_name, bhx_price_vnd, winmart_price_vnd, price_diff_vnd, price_diff_pct
     FROM dbo.vw_PriceComparison WHERE run_id = ? ORDER BY ABS(price_diff_pct) DESC''', RUN_ID)
""")

code("conn.close()")

md("""
## 13. Limitations and next steps
- **One snapshot in time**: one run per day so far; price history needs more runs (Report 3).
- **Price context**: BHX = default area without an address; WinMart = store 1535. Other areas may have other prices.
- **No barcode on BHX**, so matching uses brand + size + pack + variant + name rules; borderline cases are NEEDS_REVIEW.
- **Category coverage**: 7 groups only; fresh food (meat, vegetables) is not comparable by brand and was left out.
- **Size/pack parsing** is rule-based; rows without a size are kept but cannot be matched.
- **Website changes**: if the sites change their pages, selectors and JSON fields must be updated.

Next (Report 3): collect several runs, review NEEDS_REVIEW pairs, analyse price differences by category and over time.
""")

nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3"}})
out = Path(__file__).with_name("Report2_Data_Collection_Storage.ipynb")
nbf.write(nb, out)
print("written", out)
