"""Step 5b - Spot-check matched pairs directly on the live product pages.

For a random sample of MATCHED pairs we open BOTH product pages (BHX and WinMart) and check:
  - the page title describes the same product (word overlap with the stored name >= 0.5,
    because BHX product pages use a slightly different title than the category list),
  - the stored price appears on the page. For a WinMart secondary selling unit (e.g. 'Gói' of a
    product shown as 'Thùng'), we click that unit first, like a visitor choosing 'Chọn loại'.
Strict price check: BHX -> schema.org Product offers.price of the page; WinMart -> the price after
'Giá khuyến mại' / 'Giá bán lẻ'. Prices can change after collection: then price_match = False, reported as is.
Results (URL, time checked, what was found) are saved to reports_py/sample_verification.json.

Usage: python -m report2.verify_samples --n 12
"""
import argparse
import json
import random  # noqa: F401  (sampling is done by pandas with a fixed seed)
import re
import time

import pandas as pd
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from report2 import settings
from report2.parsing import jaccard, name_tokens, normalize_text, parse_price

_ANY_PRICE = re.compile(r"\d{1,3}(?:\.\d{3})+\s*[₫đ]")
_BHX_TITLE_SUFFIX = re.compile(r"\s*(giá tốt\s*)?tại Bách ho[aá] XANH.*$", re.I)   # '... giá tốt tại Bách hoá XANH' 


def page_prices(text: str) -> list[int]:
    return [parse_price(m) for m in _ANY_PRICE.findall(text.replace("\xa0", " "))]


def bhx_main_price(page) -> int | None:
    """BHX product pages carry schema.org Product data: offers.price is the price of THIS product."""
    for raw in page.eval_on_selector_all('script[type="application/ld+json"]', "els => els.map(e => e.textContent)"):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for node in (data.get("@graph", [data]) if isinstance(data, dict) else data):
            if isinstance(node, dict) and node.get("@type") == "Product" and isinstance(node.get("offers"), dict):
                return parse_price(float(node["offers"].get("price") or 0)) or None
    return None


def winmart_main_price(text: str) -> int | None:
    """WinMart shows 'Giá khuyến mại X ₫' (promotion) or 'Giá bán lẻ X ₫' for the selected unit."""
    for label in ("Giá khuyến mại", "Giá bán lẻ"):
        match = re.search(label + r"\s*(\d{1,3}(?:\.\d{3})+)", text.replace("\xa0", " "))
        if match:
            return parse_price(match.group(1))
    return None


def check_page(page, url: str, name: str, price: int, unit_label: str | None = None) -> dict:
    result = {"url": url, "checked_at": settings.now_vn().isoformat(timespec="seconds"), "stored_price": price}
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=settings.PAGE_TIMEOUT_MS)
        page.wait_for_timeout(4000)
        if unit_label:  # WinMart: choose the selling unit we stored (e.g. 'GÓI')
            boxes = page.locator("div.box")
            wanted = normalize_text(unit_label)
            option = next((boxes.nth(i) for i in range(boxes.count())
                           if normalize_text(boxes.nth(i).inner_text()) == wanted), None)
            if option is not None:
                option.click()
                page.wait_for_timeout(1500)
                result["unit_selected"] = unit_label
            else:
                result["unit_selected"] = f"not found: {unit_label}"
        title = _BHX_TITLE_SUFFIX.sub("", page.title())
        text = page.locator("body").inner_text()
        prices = page_prices(text)
        main_price = bhx_main_price(page) if "bachhoaxanh" in url else winmart_main_price(text)
        result.update({
            "page_title": title,
            "title_similarity": round(jaccard(name_tokens(name), name_tokens(title)), 2),
            "prices_on_page": prices[:12],
            "price_found_anywhere": price in prices,
            "page_main_price": main_price,
            "price_match": main_price == price,     # strict: the product's own current price
        })
        result["name_ok"] = result["title_similarity"] >= 0.5
    except PlaywrightError as exc:
        result["error"] = str(exc).splitlines()[0][:200]
    return result


def run(n: int, seed: int) -> dict:
    matched = pd.read_csv(settings.PROCESSED_DIR / "matched_products.csv")
    clean = pd.read_csv(settings.PROCESSED_DIR / "clean_observations.csv", usecols=["observation_id", "uom_is_primary"])
    primary = dict(zip(clean["observation_id"], clean["uom_is_primary"]))
    sample = matched.sample(n=min(n, len(matched)), random_state=seed)
    checks = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(locale="vi-VN").new_page()
        for _, row in sample.iterrows():
            pair = {"brand": row["brand"], "bhx_name": row["bhx_name"], "winmart_name": row["winmart_name"],
                    "bhx_collected_at": row["bhx_collected_at"], "winmart_collected_at": row["winmart_collected_at"]}
            pair["bhx"] = check_page(page, row["bhx_url"], row["bhx_name"], int(row["bhx_price_vnd"]))
            time.sleep(settings.DELAY_BETWEEN_PAGES_S)
            secondary = not bool(primary.get(row["winmart_observation_id"], True))
            pair["winmart"] = check_page(page, row["winmart_url"], row["winmart_name"], int(row["winmart_price_vnd"]),
                                         row["winmart_unit_label"] if secondary else None)
            time.sleep(settings.DELAY_BETWEEN_PAGES_S)
            checks.append(pair)
        browser.close()

    def count(side, key):
        return sum(1 for c in checks if c[side].get(key))
    summary = {"sample_size": len(checks), "seed": seed, "matched_pairs_total": len(matched),
               "bhx_title_matches": count("bhx", "name_ok"), "bhx_price_match": count("bhx", "price_match"),
               "winmart_title_matches": count("winmart", "name_ok"), "winmart_price_match": count("winmart", "price_match"),
               "bhx_price_found_anywhere": count("bhx", "price_found_anywhere"),
               "winmart_price_found_anywhere": count("winmart", "price_found_anywhere"),
               "errors": sum(1 for c in checks for s in ("bhx", "winmart") if c[s].get("error"))}
    report = {"summary": summary, "pairs": checks}
    (settings.REPORTS_DIR / "sample_verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Spot-check matched pairs on the live websites")
    parser.add_argument("--n", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    run(args.n, args.seed)


if __name__ == "__main__":
    main()
