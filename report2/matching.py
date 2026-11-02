"""Step 3 - Product Matching between Bach Hoa Xanh and WinMart.

We never match on "similar name" alone. A pair is only compared if ALL these agree:
  1. brand            equal brand_key ('TH true MILK' == 'TH TRUE MILK'), a listed alias
                      (config/report2_brand_aliases.json), or one store's brand written inside the
                      other store's product name (BHX brand 'Hảo Hảo' / WinMart 'Mì Hảo Hảo ...' brand ACECOOK)
  2. size per unit    (after converting kg->g, L->ml: '1L' == '1000ml')
  3. pack count       ('Thùng 48 hộp' == 48 units)
Then two more checks:
  4. variant words    (flavour, sugar level, product line) must not conflict: 'dâu' vs 'socola';
                      process words ('tiệt trùng' vs 'thanh trùng') conflict only if both names state one
  5. name similarity  (share of meaningful words, Jaccard) must be high enough, and the names must
                      not each contain a distinctive word the other lacks ('Classic' vs 'Gentleman')

Result for every BHX product:
  MATCHED       all 5 checks pass strongly and the pair is one-to-one (unique)
  NEEDS_REVIEW  same brand+size+pack but weaker name evidence, a missing variant word on one
                side, or several equally good candidates  -> NOT used in the comparison table
  NOT_MATCHED   no WinMart product passes checks 1-4

Usage: python -m report2.matching            (latest run)
       python -m report2.matching --run run_20261012_1612
"""
import argparse
import json

import pandas as pd

from report2 import settings
from report2.parsing import (REVIEW_ONLY_GROUPS, distinctive_extras, exclusive_attributes, jaccard,
                             name_tokens, normalize_text, variant_words)

STRONG_SIMILARITY = 0.5      # MATCHED needs at least this word overlap
REVIEW_SIMILARITY = 0.3      # below this the candidate is rejected
AMBIGUITY_MARGIN = 0.05      # two candidates closer than this -> ambiguous
MAX_TIME_GAP_HOURS = 3       # both prices must be collected within this time window
MIN_BRAND_KEY_IN_NAME = 4    # brand-in-name evidence only for brand keys of 4+ characters
MAX_ONE_SIDED_EXTRAS = 2      # one name has 2+ distinctive words the other lacks -> NEEDS_REVIEW


def load_manufacturers() -> dict:
    """product brand -> its manufacturer (e.g. 'haohao' -> 'acecook')."""
    path = settings.ROOT / "config" / "report2_brand_aliases.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return {brand: maker for maker, brands in data.get("manufacturers", {}).items() for brand in brands}


MANUFACTURERS = load_manufacturers()


def load_brand_aliases() -> dict:
    path = settings.ROOT / "config" / "report2_brand_aliases.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {alias: canonical for canonical, aliases in data.get("aliases", {}).items() for alias in aliases}


def prepare(df: pd.DataFrame, aliases: dict) -> pd.DataFrame:
    df = df.copy()
    df["match_brand"] = df["brand_key"].map(lambda b: aliases.get(b, b) if isinstance(b, str) else None)
    # use both the short and the long name, since they sometimes carry different details
    text = df["name_clean"].fillna("") + " " + df["spec_flavor"].fillna("")
    df["variants"] = text.map(variant_words)
    df["exclusive"] = df["name_clean"].map(exclusive_attributes)
    df["name_keys"] = df["name_clean"].map(_word_runs)
    df["tokens"] = df.apply(lambda r: name_tokens(r["name_clean"], r["brand"]), axis=1)
    df["brand_words"] = df["brand"].map(lambda v: set(normalize_text(v).split()) if isinstance(v, str) else set())
    return df


def _word_runs(name, max_words: int = 4) -> set[str]:
    """Runs of 1-4 consecutive words joined without spaces: 'mi hao hao' -> {'mi', 'hao', 'haohao', 'mihao', ...}.
    A brand must equal one of these runs, so 'oliv' does NOT match inside the word 'olive'."""
    words = normalize_text(name).replace(".", " ").split()
    return {"".join(words[i:i + n]) for n in range(1, max_words + 1) for i in range(len(words) - n + 1)}


def brand_evidence(b: pd.Series, w: pd.Series) -> str | None:
    """How do we know the brand is the same? None = no evidence."""
    bb, wb = b["match_brand"], w["match_brand"]
    if isinstance(bb, str) and bb == wb:
        return "brand_equal"
    if isinstance(bb, str) and len(bb) >= MIN_BRAND_KEY_IN_NAME and bb in w["name_keys"]:
        return "bhx_brand_in_winmart_name"
    if isinstance(wb, str) and len(wb) >= MIN_BRAND_KEY_IN_NAME and wb in b["name_keys"]:
        return "winmart_brand_in_bhx_name"
    return None


def compare(b: pd.Series, w: pd.Series, known_brands: frozenset = frozenset()) -> dict:
    """Score one BHX/WinMart candidate pair (they already share brand, size and pack)."""
    # remove BOTH stores' brand words from both names ('Nhất Ca' vs 'Tam Thái Tử' are brand words, not descriptors)
    brand_words = b["brand_words"] | w["brand_words"]
    tokens_b, tokens_w = b["tokens"] - brand_words, w["tokens"] - brand_words
    similarity = round(jaccard(tokens_b, tokens_w), 3)
    vb, vw = b["variants"], w["variants"]
    if vb and vw and vb != vw:
        return {"similarity": similarity, "decision": "reject", "reason": f"variant_conflict {sorted(vb)} vs {sorted(vw)}"}
    review_note = None
    for group, value in b["exclusive"].items():
        if group in w["exclusive"] and w["exclusive"][group] != value:
            note = f"{group}_conflict {value} vs {w['exclusive'][group]}"
            if group not in REVIEW_ONLY_GROUPS:
                return {"similarity": similarity, "decision": "reject", "reason": note}
            review_note = note
    if similarity < REVIEW_SIMILARITY:
        return {"similarity": similarity, "decision": "reject", "reason": "low_name_similarity"}
    if vb != vw:
        return {"similarity": similarity, "decision": "review", "reason": f"variant_only_one_side {sorted(vb ^ vw)}"}
    if similarity < STRONG_SIMILARITY:
        return {"similarity": similarity, "decision": "review", "reason": "medium_name_similarity"}
    extra_b, extra_w = distinctive_extras(tokens_b, tokens_w)
    pair_brands = {k for k in (b["match_brand"], w["match_brand"], b["brand_key"], w["brand_key"]) if isinstance(k, str)}
    pair_brands |= {MANUFACTURERS[k] for k in pair_brands if k in MANUFACTURERS}   # 'Hảo Hảo' is made by Acecook
    # a word that is ANOTHER brand in our data (not one of this pair's brands), e.g. 'Reeva'
    other_brand = ((extra_b | extra_w) & known_brands) - pair_brands
    if other_brand:
        return {"similarity": similarity, "decision": "review", "reason": f"other_brand_word {sorted(other_brand)}"}
    if extra_b and extra_w:  # each name says something the other does not (e.g. 'Classic' vs 'Gentleman')
        return {"similarity": similarity, "decision": "review",
                "reason": f"different_descriptors {sorted(extra_b)} vs {sorted(extra_w)}"}
    if max(len(extra_b), len(extra_w)) >= MAX_ONE_SIDED_EXTRAS:  # e.g. WinMart adds 'Big Bang' to the name
        return {"similarity": similarity, "decision": "review",
                "reason": f"extra_descriptors_one_side {sorted(extra_b | extra_w)}"}
    if review_note:
        return {"similarity": similarity, "decision": "review", "reason": review_note}
    return {"similarity": similarity, "decision": "strong", "reason": "brand+size+pack+variant+name"}


def match(clean: pd.DataFrame, run_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    aliases = load_brand_aliases()
    data = prepare(clean[clean["run_id"] == run_id], aliases)
    bhx = data[data["store"] == "bhx"].reset_index(drop=True)
    wm = data[data["store"] == "winmart"].reset_index(drop=True)

    # single-word brand keys of every product (e.g. 'reeva'), used to spot a sub-brand inside a name
    known_brands = frozenset(k for k in data["match_brand"].dropna() if k.isalpha() and len(k) >= MIN_BRAND_KEY_IN_NAME)

    # ---- 1-3: blocking on size + pack, then brand evidence
    key = ["size_value", "size_unit", "pack_count"]
    complete_b = bhx.dropna(subset=key)
    complete_w = wm.dropna(subset=key)
    pairs = complete_b.reset_index()[["index", *key]].merge(complete_w.reset_index()[["index", *key]],
                                                            on=key, suffixes=("_b", "_w"))

    # ---- 4-5: variant + name checks
    candidates = []
    for _, p in pairs.iterrows():
        b, w = bhx.loc[p["index_b"]], wm.loc[p["index_w"]]
        evidence = brand_evidence(b, w)
        if evidence is None:
            continue
        result = compare(b, w, known_brands)
        if result["decision"] != "reject":
            result["reason"] = f"{evidence}+size+pack+variant+name" if result["decision"] == "strong" else result["reason"]
        candidates.append({"b": p["index_b"], "w": p["index_w"], "brand_evidence": evidence, **result})
    cand = pd.DataFrame(candidates, columns=["b", "w", "brand_evidence", "similarity", "decision", "reason"])

    # ---- one-to-one assignment, best similarity first
    rank = {"strong": 0, "review": 1}
    usable = cand[cand["decision"] != "reject"].copy()
    usable["rank"] = usable["decision"].map(rank)
    usable = usable.sort_values(["rank", "similarity"], ascending=[True, False])
    used_b, used_w, chosen = set(), set(), {}
    for _, c in usable.iterrows():
        if c["b"] in used_b or c["w"] in used_w:
            continue
        rivals = usable[(usable["b"] == c["b"]) & (usable["w"] != c["w"]) & (usable["rank"] == c["rank"])
                        & (usable["similarity"] >= c["similarity"] - AMBIGUITY_MARGIN)]
        status = "MATCHED" if c["decision"] == "strong" and rivals.empty else "NEEDS_REVIEW"
        reason = c["reason"] if rivals.empty else f"ambiguous: {len(rivals) + 1} similar WinMart candidates"
        chosen[c["b"]] = (c["w"], status, reason, c["similarity"])
        used_b.add(c["b"])
        used_w.add(c["w"])

    # ---- one result row per BHX product
    rows = []
    for i, b in bhx.iterrows():
        if i in chosen:
            j, status, reason, similarity = chosen[i]
            w = wm.loc[j]
        else:
            w, similarity = None, None
            status = "NOT_MATCHED"
            rejected = cand[cand["b"] == i]
            if any(pd.isna(b[k]) for k in key):
                reason = "bhx_size_or_pack_missing"
            elif rejected.empty:
                reason = "no_winmart_product_with_same_brand_size_and_pack"
            elif (rejected["decision"] != "reject").any():
                reason = "best_candidate_already_matched_to_another_bhx_product"
            else:
                best = rejected.sort_values("similarity", ascending=False).iloc[0]
                reason, similarity = best["reason"], best["similarity"]
        rows.append(_result_row(b, w, status, reason, similarity))
    results = pd.DataFrame(rows)

    matched = results[results["status"] == "MATCHED"].copy()
    for col in ("winmart_price_vnd", "bhx_price_vnd"):
        matched[col] = pd.to_numeric(matched[col]).astype("float")
    matched["price_diff_vnd"] = matched["winmart_price_vnd"] - matched["bhx_price_vnd"]
    matched["price_diff_pct"] = (matched["price_diff_vnd"] / matched["bhx_price_vnd"] * 100).round(2)
    gap = (pd.to_datetime(matched["winmart_collected_at"], utc=True)
           - pd.to_datetime(matched["bhx_collected_at"], utc=True)).abs()
    matched["time_gap_minutes"] = (gap.dt.total_seconds() / 60).round(1)
    matched["price_comparable"] = (matched["bhx_price_vnd"] > 0) & (matched["winmart_price_vnd"] > 0) \
        & (matched["time_gap_minutes"] <= MAX_TIME_GAP_HOURS * 60)
    matched["cheaper_store"] = matched["price_diff_vnd"].map(
        lambda d: "same_price" if d == 0 else ("bhx" if d > 0 else "winmart"))
    return results, matched


def _result_row(b, w, status, reason, similarity) -> dict:
    def g(row, col):
        return None if row is None else row[col]
    return {
        "status": status, "reason": reason, "name_similarity": similarity, "match_brand": b["match_brand"],
        "brand": b["brand"], "size_value": b["size_value"], "size_unit": b["size_unit"], "pack_count": b["pack_count"],
        "bhx_variants": ", ".join(sorted(b["variants"])), "winmart_variants": None if w is None else ", ".join(sorted(w["variants"])),
        "bhx_observation_id": b["observation_id"], "bhx_product_code": b["product_code"], "bhx_name": b["name_clean"],
        "bhx_price_vnd": b["sale_price_vnd"], "bhx_list_price_vnd": b["list_price_vnd"], "bhx_url": b["product_url"],
        "bhx_collected_at": b["collected_at"],
        "winmart_observation_id": g(w, "observation_id"), "winmart_product_code": g(w, "product_code"),
        "winmart_barcode": g(w, "barcode"), "winmart_brand": g(w, "brand"), "winmart_name": g(w, "name_clean"),
        "winmart_unit_label": g(w, "unit_label"), "winmart_pack_source": g(w, "pack_source"),
        "bhx_unit_label": b["unit_label"],
        "winmart_price_vnd": g(w, "sale_price_vnd"), "winmart_list_price_vnd": g(w, "list_price_vnd"),
        "winmart_url": g(w, "product_url"), "winmart_collected_at": g(w, "collected_at"),
        "run_id": b["run_id"], "group": b["group"],
    }


def summary(results: pd.DataFrame, matched: pd.DataFrame, clean_run: pd.DataFrame) -> dict:
    wm_total = int((clean_run["store"] == "winmart").sum())
    wm_used = int(results["winmart_observation_id"].notna().sum())
    return {
        "run_id": results["run_id"].iloc[0] if len(results) else None,
        "bhx_products": len(results), "winmart_products": wm_total,
        "status_counts": {k: int(v) for k, v in results["status"].value_counts().items()},
        "not_matched_reasons": {k: int(v) for k, v in results.loc[results["status"] == "NOT_MATCHED", "reason"].value_counts().items()},
        "needs_review_reasons": {k: int(v) for k, v in results.loc[results["status"] == "NEEDS_REVIEW", "reason"].str.split(" ").str[0].value_counts().items()},
        "winmart_products_without_pair": wm_total - wm_used,
        "matched_by_group": {k: int(v) for k, v in matched["group"].value_counts().items()},
        "price_comparable_pairs": int(matched["price_comparable"].sum()) if len(matched) else 0,
        "cheaper_store_counts": {k: int(v) for k, v in matched.loc[matched["price_comparable"], "cheaper_store"].value_counts().items()} if len(matched) else {},
        "price_diff_pct": matched.loc[matched["price_comparable"], "price_diff_pct"].describe().round(2).to_dict() if len(matched) else {},
        "thresholds": {"STRONG_SIMILARITY": STRONG_SIMILARITY, "REVIEW_SIMILARITY": REVIEW_SIMILARITY,
                       "AMBIGUITY_MARGIN": AMBIGUITY_MARGIN, "MAX_TIME_GAP_HOURS": MAX_TIME_GAP_HOURS,
                       "MAX_ONE_SIDED_EXTRAS": MAX_ONE_SIDED_EXTRAS, "MIN_BRAND_KEY_IN_NAME": MIN_BRAND_KEY_IN_NAME},
    }


def run(run_id: str | None = None) -> dict:
    clean = pd.read_csv(settings.PROCESSED_DIR / "clean_observations.csv", dtype={"product_code": str, "barcode": str})
    clean["pack_count"] = clean["pack_count"].astype("Int64")
    run_id = run_id or sorted(clean["run_id"].unique())[-1]
    results, matched = match(clean, run_id)
    results.to_csv(settings.PROCESSED_DIR / "match_results.csv", index=False, encoding="utf-8-sig")
    matched.to_csv(settings.PROCESSED_DIR / "matched_products.csv", index=False, encoding="utf-8-sig")
    info = summary(results, matched, clean[clean["run_id"] == run_id])
    settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (settings.REPORTS_DIR / "matching_summary.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(info, ensure_ascii=False, indent=1))
    return info


def main() -> None:
    parser = argparse.ArgumentParser(description="Match identical products between BHX and WinMart")
    parser.add_argument("--run", help="run id (default: latest)")
    run(parser.parse_args().run)


if __name__ == "__main__":
    main()
