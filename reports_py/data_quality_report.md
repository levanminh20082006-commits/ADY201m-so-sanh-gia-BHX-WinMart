# Data Quality Report (generated)

Generated: 2026-10-12T23:52:36+07:00  
Runs: run_20261012_1622

## Pages
- Total pages: 54 — by status: {'ok': 54}

## Rows
| Step | BHX | WinMart | Total |
|---|---|---|---|
| Raw rows (from JSON) | 1514 | 2266 | 3780 |
| Clean rows | 1412 | 2095 | 3507 |
| Rejected rows | 102 | 171 | 273 |

### Rejected by reason
- duplicate_in_run: 200
- missing_product_code: 73

Exact duplicate raw rows: 102

## Missing values in raw rows (%)
| Field | BHX | WinMart |
|---|---|---|
| name | 0.0 | 0.0 |
| brand_raw | 0.0 | 0.0 |
| sale_price_raw | 0.0 | 0.0 |
| list_price_raw | 0.0 | 0.0 |
| product_code | 4.82 | 0.0 |
| barcode | 100.0 | 0.0 |
| unit_label | 0.0 | 0.0 |
| spec_size | 94.19 | 100.0 |
| product_url | 0.0 | 0.0 |
| collected_at | 0.0 | 0.0 |

## Missing values in clean rows (%)
| Field | BHX | WinMart |
|---|---|---|
| brand | 0.07 | 0.57 |
| list_price_vnd | 0.0 | 0.1 |
| size_value | 1.7 | 7.83 |
| pack_count | 4.46 | 6.21 |
| barcode | 100.0 | 0.0 |
| unit_price_vnd_per_kg_or_l | 6.09 | 13.7 |

## Price check: JSON price vs visible card price
- bhx: {'match': 1366, 'match_flash_sale': 46}
- winmart: {'match': 1890, 'not_visible': 201, 'match_weight_unit': 4}

## Warnings kept on clean rows
- pack_count_unclear: 193
- size_not_found: 188
- brand_missing: 13
- pack_count_conflict_name_vs_unit: 32
- list_price_below_sale_price: 2

## Price summary (VND)
- bhx: {'min': 3600, 'max': 1521000, 'mean': 88380, 'promotion_share_pct': 24.6}
- winmart: {'min': 2600, 'max': 1226000, 'mean': 82631, 'promotion_share_pct': 11.2}

## Collection time range
- bhx: 2026-10-12T16:22:13+07:00 → 2026-10-12T16:38:20+07:00
- winmart: 2026-10-12T16:23:58+07:00 → 2026-10-12T16:43:18+07:00

## Price context (store / area)
- bhx: ['2546 / provinceId=1027']
- winmart: ['1535 / storeGroupCode=1998']
