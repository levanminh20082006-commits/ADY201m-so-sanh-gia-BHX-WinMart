"""Report 3 - Part 3: data preprocessing (fix errors, missing values, outliers, normalisation, encoding).

Input : data/processed_py/clean_observations.csv   (Report 2 output, never modified)
Output: data/processed_py/report3_prepared.csv     one row per observation + new columns

Rules:
- Every changed value gets a flag column (pack_fix, *_imputed), so nothing is changed silently.
- Real prices are never removed or capped: outliers are only flagged, because a 1.5M VND carton is a real price.
- Sizes are NOT invented for unit-price analysis: unit price stays empty when the size is unknown.
"""
import re

import numpy as np
import pandas as pd

from report2 import settings

CLEAN_FILE = settings.PROCESSED_DIR / "clean_observations.csv"
PREPARED_FILE = settings.PROCESSED_DIR / "report3_prepared.csv"

# Words that make a number in a name a real item count: "48 hộp", "Lốc 4", "6 cuộn", "4 x 180ml"
PACK_WORDS = ("gói|goi|lon|chai|hộp|hop|hũ|hủ|lọ|bịch|túi|cuộn|miếng|tờ|cái|vỉ|thanh|ly|cây|viên|bình|tuýp|"
              "chiếc|que|khay|bánh|quả|lốc|bao|can|cục|hạt|ống")
PREFIX_WORDS = "thùng|lốc|bộ|set|combo|hộp|gói|túi|bịch|khay|vỉ|bao"   # container words: 'Thùng 24', 'Lốc 6'
# Columns that are empty BY DESIGN (the site does not publish them / the event did not happen)
STRUCTURAL_MISSING = {
    "barcode": "BHX does not publish barcodes",
    "site_item_no": "BHX has no WinMart item number",
    "stock_qty": "BHX does not publish stock",
    "flash_sale_price_vnd": "no flash sale on this product",
    "flash_sale_start": "no flash sale on this product",
    "flash_sale_end": "no flash sale on this product",
    "promotion_text": "no promotion text shown",
    "dom_promo_line": "no promotion line on the card",
    "spec_flavor": "flavour not listed",
    "warnings": "no warning for this row",
}
NUMERIC_FEATURES = ["log_price", "discount_pct", "log_size_filled", "pack_count_filled"]


# ------------------------------------------------------------------ 1. fix wrong values
def pack_written_in_name(name: str, n: int) -> bool:
    """True if the name really says the item count n ('Thùng 24 lon', '4 x 180ml', 'Lốc 6')."""
    name = name.lower()
    return bool(re.search(rf"(?<![\d.,]){n}\s*(?:{PACK_WORDS})\b", name)
                or re.search(rf"(?<![\d.,]){n}\s*[x*×]\s*\d+(?:[.,]\d+)?\s*(?:g|gr|ml|kg|l)\b", name)  # not '200 x 195mm'
                or re.search(rf"(?:{PREFIX_WORDS})\s*{n}(?![\d.,%+])", name))


def fix_pack_count(row) -> tuple[float, str | None]:
    """Return (pack_count, reason it was changed or None)."""
    pack, name, unit = row["pack_count"], str(row["name_clean"]), str(row["unit_label"] or "")
    # a) WinMart sells a 6-pack ('Gói (Lốc) 6') of a product whose name says 'Thùng 24': the price is for the selling unit
    m = re.search(r"\(Lốc\)\s*(\d+)", unit)
    if pd.isna(pack) and m:
        return float(m.group(1)), "selling_unit_label"
    # b) '25*20g' = 25 sachets of 20 g, but only 1 was read
    m = re.search(r"(\d+)\s*[x*×]\s*\d+(?:[.,]\d+)?\s*(?:g|ml)\b", name.lower())
    if pack == 1 and m and int(m.group(1)) > 1:
        return float(m.group(1)), "n_x_size_in_name"
    # c) the number came from the product name, not from a count: 'Wake Up 247', 'Mach 3', 'Sáng Tạo 8', 'Meiji 4.3%'
    if row.get("pack_source") == "name" and pd.notna(pack) and pack > 1 and not pack_written_in_name(name, int(pack)):
        return 1.0, "number_is_part_of_name"
    return pack, None


def fix_values(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["pack_count_report2"] = df["pack_count"]                       # keep the old values as evidence
    df["unit_price_report2"] = df["unit_price_vnd_per_kg_or_l"]
    fixed = df.apply(fix_pack_count, axis=1, result_type="expand")
    df["pack_fix"] = fixed[1]
    df["pack_count"] = fixed[0].astype(float)
    # list price missing (2 WinMart rows): no promotion shown, so list price = sale price
    df["list_price_imputed"] = df["list_price_vnd"].isna()
    df["list_price_vnd"] = df["list_price_vnd"].fillna(df["sale_price_vnd"])
    # recompute the derived quantities with the corrected pack count
    df["total_quantity"] = df["size_value"] * df["pack_count"]
    df["unit_price_vnd_per_kg_or_l"] = (df["sale_price_vnd"] / df["total_quantity"] * 1000).round()
    return df


# ------------------------------------------------------------------ 2. missing values
def missing_table(df: pd.DataFrame) -> pd.DataFrame:
    """Missing % per store for every column that has missing values, with the type of missingness."""
    rows = []
    for col in df.columns[df.isna().any()]:
        by_store = df.groupby("store")[col].apply(lambda s: round(s.isna().mean() * 100, 2))
        kind = "structural" if col in STRUCTURAL_MISSING else "real gap"
        rows.append({"column": col, "missing_total": int(df[col].isna().sum()),
                     "bhx_pct": by_store.get("bhx", 0.0), "winmart_pct": by_store.get("winmart", 0.0),
                     "type": kind, "note": STRUCTURAL_MISSING.get(col, "")})
    return pd.DataFrame(rows).sort_values("missing_total", ascending=False, ignore_index=True)


def handle_missing(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["is_flash_sale"] = df["flash_sale_price_vnd"].notna()          # structural NaN -> clear yes/no flag
    df["brand_imputed"] = df["brand"].isna()
    df["brand"] = df["brand"].fillna("UNKNOWN")
    df["brand_key"] = df["brand_key"].fillna("unknown")
    # pack count: most products are sold as 1 item (mode) -> fill 1, keep a flag
    df["pack_imputed"] = df["pack_count"].isna()
    df["pack_count_filled"] = df["pack_count"].fillna(1.0)
    # size: median of the same store + category (log scale), ONLY for the model features, never for unit price
    df["size_imputed"] = df["size_value"].isna()
    log_size = np.log(df["size_value"])
    group_median = log_size.groupby([df["store"], df["category_slug"]]).transform("median")
    df["log_size_filled"] = log_size.fillna(group_median).fillna(log_size.median())
    return df


# ------------------------------------------------------------------ 3. outliers (flag, do not delete)
def iqr_bounds(s: pd.Series, k: float = 1.5) -> tuple[float, float]:
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    return q1 - k * (q3 - q1), q3 + k * (q3 - q1)


def flag_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """IQR rule on log values inside each product group (a carton and a candy are not compared)."""
    df = df.copy()
    df["log_price"] = np.log(df["sale_price_vnd"])
    df["log_unit_price"] = np.log(df["unit_price_vnd_per_kg_or_l"])
    for col, flag in (("sale_price_vnd", "price_outlier"), ("log_price", "log_price_outlier"),
                      ("log_unit_price", "unit_price_outlier")):
        groups = df.groupby("group")[col]
        lo = groups.transform(lambda s: iqr_bounds(s.dropna())[0])
        hi = groups.transform(lambda s: iqr_bounds(s.dropna())[1])
        df[flag] = df[col].notna() & ((df[col] < lo) | (df[col] > hi))
    return df


# ------------------------------------------------------------------ 4. normalisation + encoding
def scale_params(s: pd.Series) -> dict:
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    return {"min": float(s.min()), "max": float(s.max()), "mean": float(s.mean()), "std": float(s.std(ddof=0)),
            "median": float(s.median()), "iqr": float(q3 - q1)}


def normalize(df: pd.DataFrame, columns=NUMERIC_FEATURES) -> tuple[pd.DataFrame, dict]:
    """Min-max -> [0, 1]; z-score -> mean 0, std 1; robust -> (x - median) / IQR. Parameters are returned."""
    df, params = df.copy(), {}
    for col in columns:
        p = params[col] = scale_params(df[col])
        span = (p["max"] - p["min"]) or 1.0
        df[f"{col}_minmax"] = (df[col] - p["min"]) / span
        df[f"{col}_z"] = (df[col] - p["mean"]) / (p["std"] or 1.0)
        df[f"{col}_robust"] = (df[col] - p["median"]) / (p["iqr"] or 1.0)
    return df, params


def encode(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ("is_promotion", "is_flash_sale"):
        df[f"{col}_int"] = df[col].astype(int)
    dummies = pd.get_dummies(df[["store", "group"]], prefix=["store", "group"], dtype=int)
    return pd.concat([df, dummies], axis=1)


def prepare(clean: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    before = missing_table(clean)
    df = fix_values(clean)
    df = handle_missing(df)
    df = flag_outliers(df)
    df, params = normalize(df)
    df = encode(df)
    log = {
        "rows_in": len(clean), "rows_out": len(df),
        "pack_fixes": df["pack_fix"].value_counts().to_dict(),
        "pack_fix_examples": df.loc[df["pack_fix"].notna(), ["store", "name_clean", "pack_fix", "pack_count"]]
                               .head(15).to_dict("records"),
        "imputed": {"list_price": int(df["list_price_imputed"].sum()), "brand": int(df["brand_imputed"].sum()),
                    "pack_count": int(df["pack_imputed"].sum()), "size (features only)": int(df["size_imputed"].sum())},
        "unit_price_available": int(df["unit_price_vnd_per_kg_or_l"].notna().sum()),
        "outliers": {c: int(df[c].sum()) for c in ("price_outlier", "log_price_outlier", "unit_price_outlier")},
        "scaling_params": params,
        "missing_before": before.to_dict("records"),
        "missing_after_features": {c: int(df[c].isna().sum()) for c in NUMERIC_FEATURES},
    }
    return df, log


def main() -> None:
    df, log = prepare(pd.read_csv(CLEAN_FILE))
    df.to_csv(PREPARED_FILE, index=False, encoding="utf-8-sig")
    print(f"{PREPARED_FILE.name}: {len(df)} rows, pack fixes {log['pack_fixes']}, outliers {log['outliers']}")


if __name__ == "__main__":
    main()
