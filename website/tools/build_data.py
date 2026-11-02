"""Export the group's cleaned data (Report 3) to small JSON files for the static price-comparison website.

Run from the project root:  .venv\\Scripts\\python.exe website\\tools\\build_data.py
Output: website/data/products.json, website/data/pairs.json, website/data/meta.json
"""
import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PREPARED = ROOT / "data" / "processed_py" / "report3_prepared.csv"
MATCHED = ROOT / "data" / "processed_py" / "matched_products.csv"
REJECTED = ROOT / "data" / "processed_py" / "rejected_rows.csv"
RAW = ROOT / "data" / "raw_py"
OUT = ROOT / "website" / "data"

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


def main() -> None:
    df = pd.read_csv(PREPARED, encoding="utf-8-sig", dtype={"product_code": str})
    m = pd.read_csv(MATCHED, encoding="utf-8-sig")
    m = m[(m["status"] == "MATCHED") & m["price_comparable"]]

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
        "duplicates_removed": int((pd.read_csv(REJECTED, encoding="utf-8-sig")["reject_reason"] == "duplicate_in_run").sum()),
        "values_fixed": int(df["pack_fix"].notna().sum()),
        "promo_products": int(sum(1 for it in items if it["d"] or it["f"] or it["pt"])),
        "stats": stats(df, m),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    for name, obj in (("products", items), ("pairs", pairs), ("meta", meta)):
        (OUT / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(items)} products ({sum(1 for it in items if it['img'])} with photo), {len(pairs)} pairs -> {OUT}")


if __name__ == "__main__":
    main()
