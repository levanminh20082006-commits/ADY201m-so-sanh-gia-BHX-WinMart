"""Export the group's cleaned data (Report 3) to small JSON files for the static price-comparison website.

Run from the project root:  .venv\\Scripts\\python.exe website\\tools\\build_data.py
Output: website/data/products.json, website/data/pairs.json, website/data/meta.json
"""
import json
import math
import re
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from report3 import preprocess as rp          # noqa: E402  (same formulas as the reports)
from report3 import stats as rs               # noqa: E402
from report3.run import VARIABLES, duplicate_check  # noqa: E402

PREPARED = ROOT / "data" / "processed_py" / "report3_prepared.csv"
CLEAN = ROOT / "data" / "processed_py" / "clean_observations.csv"
MATCHED = ROOT / "data" / "processed_py" / "matched_products.csv"
REJECTED = ROOT / "data" / "processed_py" / "rejected_rows.csv"
RAW = ROOT / "data" / "raw_py"
REPORT4 = ROOT / "reports_py" / "report4_results.md"
OUT = ROOT / "website" / "data"
FIG_OUT = ROOT / "website" / "assets" / "report4"

GROUP_VI = {"beverages": "Đồ uống", "household_cleaning": "Tẩy rửa", "instant_food": "Mì ăn liền",
            "milk_dairy": "Sữa", "personal_care": "Chăm sóc cá nhân", "seasoning": "Gia vị",
            "snacks_confectionery": "Bánh kẹo"}
STORE_KEY = {"bhx": "b", "winmart": "w"}


def num(x, digits=0):
    """JSON-safe number: None for NaN, int when whole."""
    if x is None or (isinstance(x, float) and math.isnan(x)) or pd.isna(x):
        return None
    x = round(float(x), digits)
    return int(x) if x == int(x) else x


def text(x):
    return None if pd.isna(x) or str(x).strip() == "" else str(x).strip()


def promo_text(x):
    """Shopper-readable promotion line; WinMart's internal code ('promotionType=ZB10') says nothing to a buyer."""
    t = text(x)
    return None if t is None or t.startswith("promotionType=") else t


def products(df: pd.DataFrame) -> list[dict]:
    rows = []
    for r in df.itertuples(index=False):
        list_price = num(r.list_price_vnd)
        rows.append({
            "id": r.observation_id[:10],             # URLs are shared by WinMart's selling units, this is not
            "s": STORE_KEY[r.store],
            "g": r.group,
            "c": text(r.site_category),
            "n": r.name_clean,
            "br": None if r.brand_imputed else text(r.brand),
            "p": num(r.sale_price_vnd),
            # original price only when it is a real, higher list price (not a filled-in value)
            "l": list_price if (not r.list_price_imputed and list_price and list_price > r.sale_price_vnd) else None,
            "d": num(r.discount_pct, 1) if r.is_promotion else None,
            "pt": promo_text(r.promotion_text),
            "f": num(r.flash_sale_price_vnd) if r.is_flash_sale else None,
            "sz": None if r.size_imputed else num(r.size_value, 2),
            "su": None if r.size_imputed else text(r.size_unit),
            "pk": num(r.pack_count_filled),
            "ul": text(r.unit_label),
            # price per kg / litre is only shown when size was read from the product, never filled in
            "up": None if r.size_imputed else num(r.unit_price_vnd_per_kg_or_l),
            "u": r.product_url,
            **({"uo": 1} if r.unit_price_outlier else {}),   # IQR outlier of price per kg/l (Report 3)
        })
    return rows


def images(run_id: str) -> dict:
    """(store, product_code) -> product photo URL, read from the raw API responses of the same collection run.
    BHX: products[].avatar (key productCode). WinMart: items[].uoms[].mediaUrl (key sku = product_code)."""
    found = {}
    for f in (RAW / run_id).glob("*.json"):
        if f.name == "manifest.json":
            continue
        page = json.loads(f.read_text(encoding="utf-8"))
        for resp in page.get("responses") or []:
            data = ((resp.get("body") or {}).get("data")) or {}
            if not isinstance(data, dict):
                continue
            for p in data.get("products") or []:
                if p.get("productCode") and p.get("avatar"):
                    found.setdefault(("bhx", str(p["productCode"])), p["avatar"])
            for p in data.get("items") or []:
                for u in p.get("uoms") or [p]:
                    url = u.get("mediaUrl") or p.get("mediaUrl")
                    sku = u.get("sku") or p.get("sku")
                    if sku and url:
                        found.setdefault(("winmart", str(sku)), url)
    return found


def group_pairs(m: pd.DataFrame) -> list[dict]:
    """Per product group: how many identical pairs are cheaper at each store."""
    t = m.groupby(["group", "cheaper_store"]).size().unstack(fill_value=0)
    rows = [{"g": g, "b": int(r.get("bhx", 0)), "w": int(r.get("winmart", 0)), "=": int(r.get("same_price", 0))}
            for g, r in t.iterrows()]
    return sorted(rows, key=lambda x: -(x["b"] + x["w"] + x["="]))


def stats(df: pd.DataFrame, m: pd.DataFrame) -> dict:
    """Figures for the 'Thống kê' page: per group and store - product count, median price, % on promotion;
    price bands per store; the signed price gap of every identical pair (WinMart vs BHX, %)."""
    groups = {}
    for (g, s), d in df.groupby(["group", "store"]):
        groups.setdefault(g, {})[STORE_KEY[s]] = {"n": len(d), "med": num(d["sale_price_vnd"].median()),
                                                   "promo": num(d["is_promotion"].mean() * 100, 1)}
    bands = {}
    for s, d in df.groupby("store"):
        p = d["sale_price_vnd"]
        bands[STORE_KEY[s]] = [int((p < 20000).sum()), int(((p >= 20000) & (p < 100000)).sum()), int((p >= 100000).sum())]
    return {"groups": groups, "bands": bands, "diffs": [num(x, 1) for x in m["price_diff_pct"]]}


def plain(x):
    """Numpy scalars and NaN -> JSON-safe Python values, recursively."""
    if isinstance(x, dict):
        return {str(k): plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [plain(v) for v in x]
    if isinstance(x, np.generic):
        x = x.item()
    return None if isinstance(x, float) and math.isnan(x) else x


# How each column with gaps is handled in report3/preprocess.py
MISSING_RULES = {
    "list_price_vnd": ("thiếu thật", "Điền bằng giá bán (không có khuyến mãi), cột cờ list_price_imputed"),
    "brand": ("thiếu thật", "Điền UNKNOWN, cột cờ brand_imputed; không đoán thương hiệu"),
    "pack_count": ("thiếu thật", "27 dòng lấy theo đơn vị bán (lốc), 166 dòng còn lại điền mode = 1, cột cờ pack_imputed"),
    "size_value": ("thiếu thật", "Median theo siêu thị + danh mục, chỉ cho cột đặc trưng log_size_filled; không dùng để tính giá/kg"),
    "flash_sale_price_vnd": ("do cấu trúc", "Không có flash sale thì để trống; tạo cột is_flash_sale (có/không)"),
    "barcode": ("do cấu trúc", "BHX không công bố mã vạch; để trống"),
    "stock_qty": ("do cấu trúc", "BHX không công bố tồn kho; để trống"),
}


def report4_figures() -> list[dict]:
    """Figures, chart type, reason and findings from the Report 4 results file; the PNG files are copied next to the site."""
    text_all = REPORT4.read_text(encoding="utf-8")
    figures = []
    for block in re.split(r"(?m)^## Hình ", text_all)[1:]:
        title = block.split("\n", 1)[0].split(". ", 1)[1].strip()
        png = re.search(r"\(report4/([^)]+\.png)\)", block).group(1)
        kind = re.search(r"\*\*Loại biểu đồ:\*\* (.+)", block).group(1).strip()
        why = re.search(r"\*\*Vì sao chọn:\*\* (.+)", block).group(1).strip()
        notes = [n.strip() for n in re.findall(r"(?m)^  - (.+)$", block)]
        figures.append({"title": title, "file": png, "kind": kind, "why": why, "notes": notes})
    FIG_OUT.mkdir(parents=True, exist_ok=True)
    for fig in figures:
        shutil.copy2(ROOT / "reports_py" / "report4" / fig["file"], FIG_OUT / fig["file"])
    return figures


def academic(df: pd.DataFrame, m: pd.DataFrame, rejected: pd.DataFrame) -> dict:
    """Evidence for the 'Theo slide' page, computed with the same functions as Report 3."""
    clean = pd.read_csv(CLEAN, encoding="utf-8-sig", dtype={"product_code": str, "barcode": str})
    miss = rp.missing_table(clean).set_index("column")
    missing = [{"col": c, "n": int(miss.loc[c, "missing_total"]), "b": float(miss.loc[c, "bhx_pct"]), "w": float(miss.loc[c, "winmart_pct"]),
                "kind": kind, "rule": rule} for c, (kind, rule) in MISSING_RULES.items() if c in miss.index]
    params = rp.scale_params(df["log_price"])
    q = df.sort_values("sale_price_vnd").reset_index(drop=True)
    picks = q.iloc[[0, len(q) // 4, len(q) // 2, 3 * len(q) // 4, len(q) - 1]]
    samples = [{"name": r.name_clean, "price": float(r.sale_price_vnd), "x": float(r.log_price), "minmax": float(r.log_price_minmax),
                "z": float(r.log_price_z), "store_bhx": int(r.store_bhx), "store_winmart": int(r.store_winmart)} for r in picks.itertuples()]
    by_store = {STORE_KEY[s]: rs.describe(g["sale_price_vnd"]) for s, g in df.groupby("store")}
    rej_store = rejected["store"].value_counts().to_dict()
    return plain({
        "pages": int(df.groupby("store")["category_slug"].nunique().sum()),
        "raw": {"total": len(df) + len(rejected), "rejected": len(rejected), "reasons": rejected["reject_reason"].value_counts().to_dict(),
                "by_store": {STORE_KEY[s]: int((df["store"] == s).sum() + rej_store.get(s, 0)) for s in STORE_KEY}},
        "winmart_items": int(df.loc[df["store"] == "winmart", "site_item_no"].nunique()),
        "variables": [list(v) for v in VARIABLES],
        "dup_check": [[str(a), int(b)] for a, b in duplicate_check(clean).itertuples(index=False)],
        "pack_fixes": df["pack_fix"].value_counts().to_dict(),
        "missing": missing,
        "columns": [45, int(df.shape[1])],
        "outliers": {c: int(df[c].sum()) for c in ("log_price_outlier", "unit_price_outlier")},
        "scale": {**params, "n": len(df)},
        "samples": samples,
        "describe": by_store,
        "correlation": rs.size_price_correlation(df).to_dict("records"),
        "tests": {"pairs": rs.matched_pairs_test(m), "promo": rs.promotion_test(df), "shelves": rs.overall_price_test(df),
                  "by_group": rs.matched_by_group(m).to_dict("records")},
        "figures": report4_figures(),
    })


def main() -> None:
    df = pd.read_csv(PREPARED, encoding="utf-8-sig", dtype={"product_code": str})
    m = pd.read_csv(MATCHED, encoding="utf-8-sig")
    m = m[(m["status"] == "MATCHED") & m["price_comparable"]]
    rejected = pd.read_csv(REJECTED, encoding="utf-8-sig")

    df = df.sort_values(["group", "store", "name_clean"]).reset_index(drop=True)
    index = {oid: i for i, oid in enumerate(df["observation_id"])}
    items = products(df)
    photos = images(df["run_id"].iloc[0])
    for it, r in zip(items, df.itertuples(index=False)):
        it["img"] = photos.get((r.store, str(r.product_code)))

    pairs = []
    for r in m.itertuples(index=False):
        b, w = index[r.bhx_observation_id], index[r.winmart_observation_id]
        items[b]["m"] = items[w]["m"] = len(pairs)
        pairs.append({"b": b, "w": w, "g": r.group,
                      "bp": num(r.bhx_price_vnd), "wp": num(r.winmart_price_vnd),
                      "ch": {"bhx": "b", "winmart": "w"}.get(r.cheaper_store, "=")})

    collected = pd.to_datetime(df["collected_at"], utc=True).dt.tz_convert("Asia/Ho_Chi_Minh")
    cheaper = m["cheaper_store"].value_counts()
    within10 = float((m["price_diff_pct"].abs() <= 10).mean() * 100)
    meta = {
        "collected_from": collected.min().strftime("%d/%m/%Y %H:%M"),
        "collected_to": collected.max().strftime("%d/%m/%Y %H:%M"),
        "products": len(df),
        "by_store": {STORE_KEY[k]: int(v) for k, v in df["store"].value_counts().items()},
        "pairs": len(pairs),
        "pairs_cheaper": {"b": int(cheaper.get("bhx", 0)), "w": int(cheaper.get("winmart", 0)),
                          "=": int(cheaper.get("same_price", 0))},
        "pairs_within_10pct": round(within10, 1),
        "groups": GROUP_VI,
        "group_counts": {g: int(n) for g, n in df["group"].value_counts().items()},
        "group_pairs": group_pairs(m),
        # how the data was prepared (shown on the "Giới thiệu" page)
        "duplicates_removed": int((rejected["reject_reason"] == "duplicate_in_run").sum()),
        "values_fixed": int(df["pack_fix"].notna().sum()),
        "promo_products": int(sum(1 for it in items if it["d"] or it["f"] or it["pt"])),
        "promo_direct": int(df["is_promotion"].sum()),
        "stats": stats(df, m),
        "academic": academic(df, m, rejected),
    }
    assert len({it["id"] for it in items}) == len(items), "product ids must be unique"

    OUT.mkdir(parents=True, exist_ok=True)
    for name, obj in (("products", items), ("pairs", pairs), ("meta", meta)):
        (OUT / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(items)} products ({sum(1 for it in items if it['img'])} with photo), {len(pairs)} pairs -> {OUT}")


if __name__ == "__main__":
    main()
