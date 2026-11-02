"""Step 2 - Data Cleaning & Validation with pandas.

Input : data/raw_py/<run_id>/*.json   (raw evidence from collect.py)
Output: data/processed_py/raw_products_flat.csv   every product row found in raw JSON
        data/processed_py/clean_observations.csv  valid, de-duplicated rows (one per product per run)
        data/processed_py/rejected_rows.csv       rows removed + the reason
        reports_py/data_quality_report.json/.md   numbers for the report

Each row keeps `row_id` = run|store|category|response#|item# so it can be traced
back to the exact place in the raw JSON file.

Usage: python -m report2.clean            (all runs in data/raw_py)
       python -m report2.clean --runs run_20261012_1612
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pandas as pd

from report2 import settings
from report2.collect import end_reached
from report2.parsing import (brand_key, card_prices, clean_text, normalize_text, parse_pack_count, parse_percent,
                             parse_price, parse_size)

BHX_SIZE_SPECS = ("Dung tích", "Khối lượng", "Trọng lượng", "Thể tích")
BHX_PACK_SPEC = "Số lượng hoặc đóng gói"
BHX_FLAVOR_SPEC = "Hương vị"
# WinMart selling units that mean ONE item (normalised, no accents)
SINGLE_UNIT_WORDS = {"goi", "chai", "hop", "lon", "tuyp", "cai", "ly", "lo", "can", "khay", "hu",
                     "bich", "tui", "mieng", "qua", "to", "binh", "cay", "cuon"}


# ------------------------------------------------------------------ 1. flatten raw JSON
def _dom_index(page: dict) -> dict:
    """product_code -> first visible card (for cross-checking prices)."""
    index = {}
    for card in page.get("dom_cards", []):
        if card.get("product_code") and card["product_code"] not in index:
            index[card["product_code"]] = card
    return index


def _bhx_rows(page: dict, response: dict, r_idx: int) -> list[dict]:
    data = (response.get("body") or {}).get("data") or {}
    try:
        context = json.loads(response.get("request_body") or "{}")
    except json.JSONDecodeError:
        context = {}
    if not context:  # GetCate: context is in the query string
        context = {k: v[0] for k, v in parse_qs(urlsplit(response["url"]).query).items()}
    rows = []
    for i_idx, p in enumerate(data.get("products") or []):
        prices = p.get("productPrices") or [{}]
        specs = {s.get("propertyName"): s.get("propValue") for s in p.get("specifications") or []}
        campaign = (p.get("lstCampaingInfo") or [{}])[0]  # time-limited flash sale, if any
        size_spec = next((specs[k] for k in BHX_SIZE_SPECS if specs.get(k)), None)
        rows.append({
            "response_index": r_idx, "item_index": i_idx,
            "product_code": str(p.get("productCode") or "") or None,
            "card_key": str(p.get("productCode") or "") or None,
            "site_product_id": str(p.get("id") or "") or None, "site_item_no": None, "uom_is_primary": True,
            "barcode": None,  # BHX does not publish barcodes on its website
            "name": p.get("name"), "full_name": p.get("fullName"),
            "brand_raw": p.get("brandName"),
            "sale_price_raw": prices[0].get("price"), "list_price_raw": prices[0].get("sysPrice"),
            "discount_pct_raw": prices[0].get("discountPercent"), "n_price_entries": len(prices),
            "unit_label": p.get("unit"), "pack_qty_raw": p.get("exchangeQuantity"),
            "spec_size": size_spec, "spec_pack": specs.get(BHX_PACK_SPEC), "spec_flavor": specs.get(BHX_FLAVOR_SPEC),
            "promotion_text": p.get("promotionText") or None,
            "flash_sale_price_raw": (campaign.get("productPrice") or {}).get("price"),
            "flash_sale_start": campaign.get("startTime"), "flash_sale_end": campaign.get("dueTime"),
            "can_buy": prices[0].get("isCanBuy"), "stock_qty": None,
            "site_category": (p.get("category") or {}).get("name"),
            "product_url": "https://www.bachhoaxanh.com" + p["url"] if p.get("url") else None,
            "price_store_id": str(prices[0].get("storeId") or context.get("storeId") or "") or None,
            "price_area": f"provinceId={context.get('provinceId')}" if context.get("provinceId") else None,
        })
    return rows


def _winmart_rows(page: dict, response: dict, r_idx: int) -> list[dict]:
    """One row per selling unit (uom). WinMart sells e.g. the same noodle as 'Gói' (1) and 'Thùng' (30);
    each unit has its own SKU, price and quantityPerUnit. Only the first unit is shown on the card."""
    data = (response.get("body") or {}).get("data") or {}
    query = {k: v[0] for k, v in parse_qs(urlsplit(response["url"]).query).items()}
    rows = []
    for i_idx, p in enumerate(data.get("items") or []):
        units = p.get("uoms") or [p]
        for u_idx, u in enumerate(units):
            primary = u.get("uom", p.get("uom")) == p.get("uom")
            rows.append({
                "response_index": r_idx, "item_index": i_idx if len(units) == 1 else f"{i_idx}u{u_idx}",
                "product_code": str(u.get("sku") or p.get("sku") or p.get("itemNo") or "") or None,   # itemNo + unit, e.g. 10196814G1
                "card_key": str(p.get("itemNo") or "") if primary else None,
                "site_product_id": p.get("id"), "site_item_no": p.get("itemNo"),
                "barcode": u.get("barcode") or p.get("barcode") or None,
                "name": p.get("name"), "full_name": p.get("description"),
                "brand_raw": p.get("brandName"),
                "sale_price_raw": u.get("salePrice"), "list_price_raw": u.get("price"),
                "discount_pct_raw": None, "n_price_entries": len(units), "uom_is_primary": primary,
                "unit_label": u.get("uomName"), "pack_qty_raw": u.get("quantityPerUnit"),
                "spec_size": None, "spec_pack": None, "spec_flavor": None,
                "promotion_text": p.get("promotionCode") and f"promotionType={p.get('promotionType')}",
                "flash_sale_price_raw": None, "flash_sale_start": None, "flash_sale_end": None,
                "can_buy": (u.get("quantity") or 0) > 0, "stock_qty": u.get("quantity"),
                "site_category": p.get("categoryName") or p.get("mch4Name"),
                "product_url": (f"https://winmart.vn/products/{p['seoName']}?storeCode={query.get('storeCode')}"
                                if p.get("seoName") else None),
                "price_store_id": query.get("storeCode"),
                "price_area": f"storeGroupCode={query.get('storeGroupCode')}" if query.get("storeGroupCode") else None,
            })
    return rows


def _card_weight_kg(card_text) -> float | None:
    """WinMart weight items show e.g. '0.5KG' on the card, with the price for that weight."""
    match = re.search(r"^\s*(\d+(?:\.\d+)?)\s*KG\s*$", str(card_text or ""), flags=re.M)
    return float(match.group(1)) if match else None


def flatten_page(page: dict, raw_file: str) -> list[dict]:
    dom = _dom_index(page)
    rows = []
    for r_idx, response in enumerate(page.get("responses", [])):
        if response.get("status") != 200:
            continue
        builder = _bhx_rows if page["store"] == "bhx" else _winmart_rows
        for row in builder(page, response, r_idx):
            card = dom.get(row["card_key"]) if row["card_key"] else None
            row.update({
                "run_id": page["run_id"], "store": page["store"], "group": page["group"],
                "category_slug": page["category_slug"], "source_url": page["source_url"],
                "collected_at": page.get("collected_at") or page.get("requested_at"),
                "raw_file": raw_file,
                "row_id": f"{page['run_id']}|{page['store']}|{page['category_slug']}|r{row['response_index']}|i{row['item_index']}",
                "in_dom": card is not None,
                "dom_name": card.get("name") if card else None,
                "dom_prices": "|".join(map(str, card_prices(card.get("card_text")))) if card else None,
                "dom_weight_kg": _card_weight_kg(card.get("card_text")) if card else None,
                "dom_promo_line": next((ln for ln in (card.get("card_text") or "").splitlines()
                                        if ln.strip().lower().startswith("mua ") and "₫" in ln), None) if card else None,
            })
            rows.append(row)
    return rows


def load_raw(run_ids: list[str] | None = None) -> tuple[pd.DataFrame, list[dict]]:
    rows, pages = [], []
    run_dirs = sorted(d for d in settings.RAW_DIR.iterdir() if d.is_dir())
    for run_dir in run_dirs:
        if run_ids and run_dir.name not in run_ids:
            continue
        if not run_ids and not run_dir.name.startswith("run_"):  # trial / aborted folders are evidence only
            continue
        if not (run_dir / "manifest.json").exists():  # interrupted run: no manifest, not used
            continue
        for path in sorted(run_dir.glob("*__*.json")):
            page = json.loads(path.read_text(encoding="utf-8"))
            pages.append({"run_id": page["run_id"], "store": page["store"], "category_slug": page["category_slug"],
                          "status": page["status"], "error": page.get("error"),
                          "dom_cards": len(page.get("dom_cards", [])), "responses": len(page.get("responses", [])),
                          "end_reached": end_reached(page["store"], page.get("responses", [])),
                          "site_total_count": page.get("site_total_count")})
            rows += flatten_page(page, str(path.relative_to(settings.ROOT)).replace("\\", "/"))
    return pd.DataFrame(rows), pages


# ------------------------------------------------------------------ 2. clean + derive fields
def derive_fields(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["name_clean"] = df["name"].map(clean_text)
    df["name_normalized"] = df["name_clean"].map(lambda v: normalize_text(v) if v else None)
    df["brand"] = df["brand_raw"].map(clean_text)
    df["brand_key"] = df["brand"].map(lambda v: brand_key(v) if v else None)
    df["sale_price_vnd"] = df["sale_price_raw"].map(parse_price)
    df["list_price_vnd"] = df["list_price_raw"].map(parse_price)

    # weight / volume: BHX structured spec first, otherwise read it from the name, then the long name
    def size_of(row):
        for source, text in (("spec", row["spec_size"]), ("name", row["name_clean"]), ("full_name", row["full_name"])):
            parsed = parse_size(text) if text else None
            if parsed and parsed["size_value"]:
                return pd.Series([parsed["size_value"], parsed["size_unit"], source])
        return pd.Series([None, None, None])

    df[["size_value", "size_unit", "size_source"]] = df.apply(size_of, axis=1)
    df["size_value"] = pd.to_numeric(df["size_value"], errors="coerce")
    df["sale_price_vnd"] = pd.to_numeric(df["sale_price_vnd"], errors="coerce").astype("Int64")
    df["list_price_vnd"] = pd.to_numeric(df["list_price_vnd"], errors="coerce").astype("Int64")

    # number of units sold together (e.g. 'Thùng 48 hộp' -> 48)
    def pack_of(row):
        from_name = parse_pack_count(row["name_clean"] or "")
        if row["store"] == "winmart":
            # 1) quantityPerUnit > 1 (Thùng = 30)  2) count in the unit label ('Gói (Lốc) 4')
            qty = row["pack_qty_raw"]
            label_text = row["unit_label"] if isinstance(row["unit_label"], str) else ""
            label = parse_pack_count(label_text) if label_text else None
            site = int(qty) if qty and qty > 1 else (label if label and label > 1 else None)
            if site is not None:
                if from_name not in (None, 1, site):  # the name says another count: do not guess
                    return pd.Series([None, "conflict"])
                return pd.Series([site, "site_unit"])
            # 3) a single-item unit ('Gói', 'Chai'...) of a product that is ALSO sold in other units
            #    = one item, even if the shared name says 'Thùng 30 gói ...'
            if normalize_text(label_text) in SINGLE_UNIT_WORDS and row["n_price_entries"] > 1:
                return pd.Series([1, "site_unit"])
            # 4) otherwise only the name can tell
            return pd.Series([from_name, "name" if from_name is not None else None])
        if row["spec_pack"]:
            count = parse_pack_count(row["spec_pack"])
            if count:
                return pd.Series([count, "spec"])
        return pd.Series([from_name, "name" if from_name is not None else None])

    df[["pack_count", "pack_source"]] = df.apply(pack_of, axis=1)
    df["pack_count"] = df["pack_count"].astype("Int64")
    df["total_quantity"] = df["size_value"] * df["pack_count"].astype("float")
    df["unit_price_vnd_per_kg_or_l"] = (df["sale_price_vnd"].astype("float") / df["total_quantity"] * 1000).round(0)
    df["is_promotion"] = df["list_price_vnd"].notna() & (df["list_price_vnd"] > df["sale_price_vnd"])
    df["is_promotion"] = df["is_promotion"].fillna(False).astype(bool)
    ratio = df["sale_price_vnd"].astype("float") / df["list_price_vnd"].astype("float")
    df["discount_pct"] = ((1 - ratio) * 100).round(1).where(df["is_promotion"], 0.0)
    df["collected_at_ts"] = pd.to_datetime(df["collected_at"], errors="coerce", utc=False)
    df["flash_sale_price_vnd"] = df["flash_sale_price_raw"].map(parse_price)
    df["dom_price_check"] = df.apply(dom_check, axis=1)
    return df


def dom_check(row) -> str:
    """Compare the JSON price with the first price shown on the visible card."""
    if not row["in_dom"] or not row["dom_prices"]:
        return "not_visible"
    shown = int(str(row["dom_prices"]).split("|")[0])
    if shown == row["sale_price_vnd"]:
        return "match"
    if shown == row["flash_sale_price_vnd"]:
        return "match_flash_sale"  # card shows the time-limited flash price; we keep the regular price
    weight = row.get("dom_weight_kg")
    if weight and not pd.isna(weight) and round(row["sale_price_vnd"] * weight) == shown:
        return "match_weight_unit"  # JSON price is per kg, the card shows the price of e.g. 0.5 kg
    return "mismatch"


# ------------------------------------------------------------------ 3. validation
def reject_reason(row) -> str | None:
    """First failing rule, or None if the row is valid."""
    if not row["name_clean"]:
        return "missing_name"
    if not row["product_code"]:
        return "missing_product_code"
    if pd.isna(row["sale_price_vnd"]):
        return "missing_or_unparseable_price"
    if row["sale_price_vnd"] <= 0:
        return "price_not_positive"
    if not settings.MIN_VALID_PRICE <= row["sale_price_vnd"] <= settings.MAX_VALID_PRICE:
        return "price_out_of_range"
    if pd.isna(row["collected_at_ts"]) or row["collected_at_ts"].utcoffset() is None:
        return "invalid_or_naive_timestamp"
    return None


def validate(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.copy()
    df["reject_reason"] = df.apply(reject_reason, axis=1)
    # Duplicate = same product seen again in the same run (e.g. listed in two categories or two pages).
    valid = df["reject_reason"].isna()
    dup = valid & df.duplicated(subset=["run_id", "store", "product_code"], keep="first")
    df.loc[dup, "reject_reason"] = "duplicate_in_run"
    # Warnings keep the row but are recorded
    df["warnings"] = ""
    bad_list = df["list_price_vnd"].notna() & (df["list_price_vnd"] < df["sale_price_vnd"])
    df.loc[bad_list, "warnings"] += "list_price_below_sale_price;"
    df.loc[bad_list, "list_price_vnd"] = pd.NA  # inconsistent original price is dropped, not guessed
    df.loc[df["dom_price_check"] == "mismatch", "warnings"] += "dom_price_mismatch;"
    df.loc[df["size_value"].isna(), "warnings"] += "size_not_found;"
    df.loc[df["pack_count"].isna(), "warnings"] += "pack_count_unclear;"
    df.loc[df["pack_source"] == "conflict", "warnings"] += "pack_count_conflict_name_vs_unit;"
    df.loc[df["brand"].isna(), "warnings"] += "brand_missing;"
    df.loc[df["can_buy"] == False, "warnings"] += "not_buyable_now;"  # noqa: E712
    clean = df[df["reject_reason"].isna()].copy()
    rejected = df[df["reject_reason"].notna()].copy()
    clean["observation_id"] = clean.apply(
        lambda r: hashlib.sha1(f"{r['run_id']}|{r['store']}|{r['product_code']}".encode()).hexdigest()[:20], axis=1)
    return clean, rejected


CLEAN_COLUMNS = [
    "observation_id", "run_id", "collected_at", "store", "group", "category_slug", "site_category",
    "product_code", "site_product_id", "site_item_no", "uom_is_primary", "barcode", "name_clean", "full_name", "name_normalized", "brand", "brand_key",
    "sale_price_vnd", "list_price_vnd", "is_promotion", "discount_pct", "promotion_text",
    "flash_sale_price_vnd", "flash_sale_start", "flash_sale_end", "dom_promo_line",
    "size_value", "size_unit", "size_source", "pack_count", "pack_source", "unit_label", "spec_flavor",
    "total_quantity", "unit_price_vnd_per_kg_or_l", "can_buy", "stock_qty",
    "price_store_id", "price_area", "product_url", "source_url", "dom_price_check", "warnings",
    "raw_file", "row_id",
]


# ------------------------------------------------------------------ 4. quality report
def quality_report(raw: pd.DataFrame, clean: pd.DataFrame, rejected: pd.DataFrame, pages: list[dict]) -> dict:
    def per_store(frame):
        return {s: int(n) for s, n in frame["store"].value_counts().items()} if len(frame) else {}

    important = ["name", "brand_raw", "sale_price_raw", "list_price_raw", "product_code", "barcode",
                 "unit_label", "spec_size", "product_url", "collected_at"]
    missing = {}
    for store, part in raw.groupby("store"):
        missing[store] = {c: round(float(part[c].isna().mean() * 100), 2) for c in important}
    clean_missing = {}
    for store, part in clean.groupby("store"):
        clean_missing[store] = {c: round(float(part[c].isna().mean() * 100), 2)
                                for c in ["brand", "list_price_vnd", "size_value", "pack_count", "barcode",
                                          "unit_price_vnd_per_kg_or_l"]}
    warnings = Counter(w for ws in clean["warnings"] for w in ws.split(";") if w)
    return {
        "generated_at": settings.now_vn().isoformat(timespec="seconds"),
        "runs": sorted(raw["run_id"].unique().tolist()) if len(raw) else [],
        "pages": {"total": len(pages), "by_status": dict(Counter(p["status"] for p in pages)),
                  "failed": [p for p in pages if p["status"] != "ok"],
                  "end_not_confirmed": [f"{p['store']}/{p['category_slug']}" for p in pages
                                        if p["status"] == "ok" and not p.get("end_reached")]},
        "rows": {"raw_rows": len(raw), "raw_by_store": per_store(raw),
                 "clean_rows": len(clean), "clean_by_store": per_store(clean),
                 "rejected_rows": len(rejected), "rejected_by_store": per_store(rejected),
                 "rejected_by_reason": {k: int(v) for k, v in rejected["reject_reason"].value_counts().items()}},
        "distinct_products_by_store": {s: int(n) for s, n in clean.groupby("store")["product_code"].nunique().items()},
        "exact_duplicate_raw_rows": int(raw.drop(columns=["row_id", "response_index", "item_index"]).astype(str).duplicated().sum()),
        "missing_pct_raw": missing,
        "missing_pct_clean": clean_missing,
        "dom_price_check_clean": {s: dict(Counter(p["dom_price_check"])) for s, p in clean.groupby("store")},
        "warnings_clean": dict(warnings),
        "price_summary_clean": {s: {"min": int(p["sale_price_vnd"].min()), "max": int(p["sale_price_vnd"].max()),
                                    "mean": round(float(p["sale_price_vnd"].mean())),
                                    "promotion_share_pct": round(float(p["is_promotion"].mean() * 100), 1)}
                                for s, p in clean.groupby("store")},
        "collected_at_range": {s: [str(p["collected_at"].min()), str(p["collected_at"].max())]
                               for s, p in clean.groupby("store")},
        "price_context": {s: sorted({f"{a} / {b}" for a, b in zip(p["price_store_id"], p["price_area"])})
                          for s, p in clean.groupby("store")},
    }


def write_markdown(report: dict, path: Path) -> None:
    r = report["rows"]
    lines = ["# Data Quality Report (generated)", "", f"Generated: {report['generated_at']}  ",
             f"Runs: {', '.join(report['runs'])}", "",
             "## Pages", f"- Total pages: {report['pages']['total']} — by status: {report['pages']['by_status']}", "",
             "## Rows", "| Step | BHX | WinMart | Total |", "|---|---|---|---|"]
    for label, key in (("Raw rows (from JSON)", "raw_by_store"), ("Clean rows", "clean_by_store"),
                       ("Rejected rows", "rejected_by_store")):
        d = r[key]
        lines.append(f"| {label} | {d.get('bhx', 0)} | {d.get('winmart', 0)} | {sum(d.values())} |")
    lines += ["", "### Rejected by reason", *[f"- {k}: {v}" for k, v in r["rejected_by_reason"].items()],
              "", f"Exact duplicate raw rows: {report['exact_duplicate_raw_rows']}", "",
              "## Missing values in raw rows (%)", "| Field | BHX | WinMart |", "|---|---|---|"]
    stores = report["missing_pct_raw"]
    for field in next(iter(stores.values()), {}):
        lines.append(f"| {field} | {stores.get('bhx', {}).get(field, '')} | {stores.get('winmart', {}).get(field, '')} |")
    lines += ["", "## Missing values in clean rows (%)", "| Field | BHX | WinMart |", "|---|---|---|"]
    stores = report["missing_pct_clean"]
    for field in next(iter(stores.values()), {}):
        lines.append(f"| {field} | {stores.get('bhx', {}).get(field, '')} | {stores.get('winmart', {}).get(field, '')} |")
    lines += ["", "## Price check: JSON price vs visible card price", *[f"- {s}: {v}" for s, v in report["dom_price_check_clean"].items()],
              "", "## Warnings kept on clean rows", *[f"- {k}: {v}" for k, v in report["warnings_clean"].items()],
              "", "## Price summary (VND)", *[f"- {s}: {v}" for s, v in report["price_summary_clean"].items()],
              "", "## Collection time range", *[f"- {s}: {v[0]} → {v[1]}" for s, v in report["collected_at_range"].items()],
              "", "## Price context (store / area)", *[f"- {s}: {v}" for s, v in report["price_context"].items()]]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(run_ids: list[str] | None = None) -> dict:
    raw, pages = load_raw(run_ids)
    if raw.empty:
        raise SystemExit("No raw product rows found in data/raw_py")
    df = derive_fields(raw)
    clean, rejected = validate(df)
    settings.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    raw.to_csv(settings.PROCESSED_DIR / "raw_products_flat.csv", index=False, encoding="utf-8-sig")
    clean[CLEAN_COLUMNS].to_csv(settings.PROCESSED_DIR / "clean_observations.csv", index=False, encoding="utf-8-sig")
    rejected[["row_id", "run_id", "store", "category_slug", "product_code", "name", "sale_price_raw",
              "collected_at", "reject_reason", "raw_file"]].to_csv(
        settings.PROCESSED_DIR / "rejected_rows.csv", index=False, encoding="utf-8-sig")
    report = quality_report(raw, clean, rejected, pages)
    (settings.REPORTS_DIR / "data_quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    write_markdown(report, settings.REPORTS_DIR / "data_quality_report.md")
    print(json.dumps(report["rows"], ensure_ascii=False, indent=1))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean and validate raw product data")
    parser.add_argument("--runs", nargs="*", help="run ids to include (default: all)")
    run(parser.parse_args().runs)


if __name__ == "__main__":
    main()
