"""Step 1 - Data Collection with Playwright.

How it works (for each category page):
1. Check robots.txt allows the URL.
2. Open the public category page in Chromium, like a normal visitor.
3. Scroll down until no new product cards appear (infinite scroll).
4. Save two kinds of evidence, both exactly as received:
   - dom_cards: text of every product card visible on the page (name, prices)
   - responses: the product-list JSON responses the page itself downloaded
     while rendering (we only *listen*; we never call these APIs ourselves).
5. Write one raw JSON file per page into data/raw_py/<run_id>/.

We do NOT log in, solve CAPTCHAs or bypass any protection. If a page looks
blocked or shows no products, it is recorded as failed and skipped.

Usage:
    python -m report2.collect                       # all groups
    python -m report2.collect --groups milk_dairy --max-pages 2   # small test
"""
import argparse
import json
import logging
import re
import time
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from report2 import settings
from report2.robots import fetch_robots, is_allowed

# Product-list JSON responses we keep (requested by the page itself).
RESPONSE_PATTERNS = {
    "bhx": [re.compile(r"/Category/AjaxProduct"), re.compile(r"/Category/V2/GetCate\?")],
    "winmart": [re.compile(r"/api/web/v\d+/item/category\?")],
}
CARD_SELECTOR = {"bhx": ".box_product", "winmart": ".product-card"}
BLOCK_HINTS = re.compile(r"captcha|access denied|forbidden|too many requests|bị chặn", re.I)

# JavaScript run inside the page to read the visible product cards.
DOM_JS = {
    "bhx": """
() => [...document.querySelectorAll('.box_product')].map((card, i) => {
  const priceEl = card.querySelector('.product_price');
  let priceText = '';
  if (priceEl) priceEl.childNodes.forEach(n => { if (n.nodeType === 3) priceText += n.textContent; });
  const link = card.querySelector('a[href]');
  const badge = [...card.querySelectorAll('span')].map(s => s.textContent.trim()).find(t => /^-\\s*\\d+%$/.test(t));
  return {
    position: i,
    product_code: card.querySelector('[product-code]')?.getAttribute('product-code') || null,
    site_id: (card.querySelector('a[id^="product_"]')?.id || '').replace('product_', '') || null,
    url: link ? link.href : null,
    name: card.querySelector('h3.product_name')?.textContent.trim() || null,
    price_text: priceText.trim() || null,
    price_unit_label: priceEl?.querySelector('div')?.textContent.trim() || null,
    original_price_text: card.querySelector('.line-through')?.textContent.trim() || null,
    discount_badge: badge || null,
    card_text: card.innerText
  };
})""",
    "winmart": """
() => [...document.querySelectorAll('.product-card')].map((card, i) => {
  const link = card.querySelector('a[href*="/products/"]');
  const priceTexts = [...card.querySelectorAll('.bottom-wrapper div')]
     .filter(d => d.children.length === 0 && /^[\\d.]+\\s*\\u20ab$/.test(d.textContent.replace(/\\u00a0/g, ' ').trim()))
     .map(d => d.textContent.trim());
  const badge = [...card.querySelectorAll('div')].map(d => d.textContent.trim()).find(t => /^-\\s*\\d+%$/.test(t));
  return {
    position: i,
    product_code: link ? ((link.href.match(/--s(\\d+)/) || [])[1] || null) : null,
    site_id: null,
    url: link ? link.href : null,
    name: card.querySelector('img.product-image')?.alt?.trim() || card.querySelector('[aria-label]')?.getAttribute('aria-label') || null,
    price_text: priceTexts[0] || null,
    price_unit_label: card.querySelector('div[style*="opacity"]')?.textContent.trim() || null,
    original_price_text: priceTexts[1] || null,
    discount_badge: badge || null,
    card_text: card.innerText
  };
})""",
}

log = logging.getLogger("collect")


def setup_logging() -> None:
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
    handlers = [logging.FileHandler(settings.LOG_DIR / "report2_collect.log", encoding="utf-8"),
                logging.StreamHandler()]
    logging.basicConfig(level=logging.INFO, handlers=handlers,
                        format="%(asctime)s %(levelname)s %(message)s")


def category_url(store: str, slug: str, sources: dict) -> str:
    base = sources["stores"][store]["base_url"]
    if store == "winmart":
        return f"{base}/{slug}?storeCode={sources['stores']['winmart']['store_code']}"
    return f"{base}/{slug}"


def _items_in(store: str, response: dict) -> int | None:
    data = ((response.get("body") or {}).get("data")) or {}
    items = data.get("products") if store == "bhx" else data.get("items")
    return len(items) if isinstance(items, list) else None


def _requested_page_size(store: str, response: dict) -> int | None:
    if store == "winmart":
        match = re.search(r"pageSize=(\d+)", response["url"])
        return int(match.group(1)) if match else None
    match = (re.search(r'"PageSize"\s*:\s*(\d+)', response.get("request_body") or "")
             or re.search(r"[?&]pageSize=(\d+)", response["url"]))   # GetCate sends it in the URL
    return int(match.group(1)) if match else None


def end_reached(store: str, responses: list[dict]) -> bool:
    """The site has no more products when the last list page returned fewer items than requested."""
    pages = [r for r in responses if _requested_page_size(store, r)]
    if not pages:
        return False
    last = pages[-1]
    paging = (last.get("body") or {}).get("paging") or {}   # WinMart tells us the total pages
    if paging.get("totalPages"):
        return paging.get("pageNumber", 0) >= paging["totalPages"]
    size, got = _requested_page_size(store, last), _items_in(store, last)
    return got is not None and got < size


def scroll_until_stable(page, store: str, responses: list[dict]) -> list[int]:
    """Scroll to the bottom until the site's last page is reached or no new cards load."""
    selector = CARD_SELECTOR[store]
    counts, stable = [page.locator(selector).count()], 0
    for _ in range(settings.MAX_SCROLL_ROUNDS):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1200)
        page.mouse.wheel(0, -600)   # small move up/down so lazy loaders notice the scroll
        page.mouse.wheel(0, 1200)
        page.wait_for_timeout(1800)
        counts.append(page.locator(selector).count())
        if end_reached(store, responses):
            break
        stable = stable + 1 if counts[-1] == counts[-2] else 0
        if stable >= settings.STABLE_ROUNDS_TO_STOP:
            break
    return counts


def scrape_page(context, store: str, group: str, slug: str, url: str, run_id: str) -> dict:
    """Open one category page and return the raw evidence record."""
    record = {"run_id": run_id, "store": store, "group": group, "category_slug": slug,
              "source_url": url, "requested_at": settings.now_vn().isoformat(timespec="seconds"),
              "status": "failed", "error": None, "responses": [], "dom_cards": []}
    page = context.new_page()

    def on_response(response):
        if not any(p.search(response.url) for p in RESPONSE_PATTERNS[store]):
            return
        item = {"url": response.url, "status": response.status, "method": response.request.method,
                "request_body": response.request.post_data,
                "received_at": settings.now_vn().isoformat(timespec="seconds")}
        try:
            item["body"] = response.json()
        except Exception as exc:  # non-JSON or body not available
            item["body"], item["body_error"] = None, repr(exc)
        record["responses"].append(item)

    page.on("response", on_response)
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=settings.PAGE_TIMEOUT_MS)
        record["http_status"] = resp.status if resp else None
        page.wait_for_timeout(4000)
        record["page_title"] = page.title()
        record["final_url"] = page.url
        if record["http_status"] and record["http_status"] >= 400:
            raise RuntimeError(f"HTTP {record['http_status']}")
        if BLOCK_HINTS.search(record["page_title"] or ""):
            raise RuntimeError(f"page looks blocked: {record['page_title']!r}")
        record["scroll_card_counts"] = scroll_until_stable(page, store, record["responses"])
        page.wait_for_timeout(1500)  # let the last responses arrive
        record["end_reached"] = end_reached(store, record["responses"])
        paging = [(r.get("body") or {}).get("paging") for r in record["responses"]]
        totals = [p_["totalCount"] for p_ in paging if p_ and p_.get("totalCount") is not None]
        record["site_total_count"] = totals[-1] if totals else None  # only WinMart reports this
        record["dom_cards"] = page.evaluate(DOM_JS[store])
        record["collected_at"] = settings.now_vn().isoformat(timespec="seconds")
        record["status"] = "ok" if record["dom_cards"] else "no_items"
    except (PlaywrightError, RuntimeError) as exc:
        record["error"] = f"{type(exc).__name__}: {str(exc).splitlines()[0][:300]}"
    finally:
        page.close()
    return record


def run(groups_filter: list[str] | None, max_pages: int | None, run_id: str | None,
        only: list[str] | None = None) -> Path:
    sources = json.loads(settings.SOURCES_FILE.read_text(encoding="utf-8"))
    run_id = run_id or "run_" + settings.now_vn().strftime("%Y%m%d_%H%M")
    out_dir = settings.RAW_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    robots = {}
    for store, info in sources["stores"].items():
        robots[store] = fetch_robots(info["base_url"])
        (out_dir / f"robots_{store}.txt").write_text(robots[store], encoding="utf-8")

    jobs = []  # interleave stores group by group so prices are collected close in time
    for g in sources["groups"]:
        if groups_filter and g["group"] not in groups_filter:
            continue
        for store in ("bhx", "winmart"):
            jobs += [(store, g["group"], slug) for slug in g[store]]
    if only:  # re-collect selected pages ('store/slug') into an existing run
        jobs = [j for j in jobs if f"{j[0]}/{j[2]}" in only]
    if max_pages:
        jobs = jobs[:max_pages]

    old_manifest = out_dir / "manifest.json"
    previous = json.loads(old_manifest.read_text(encoding="utf-8")) if only and old_manifest.exists() else None
    manifest = {"run_id": run_id, "started_at": settings.now_vn().isoformat(timespec="seconds"),
                "settings": {k: getattr(settings, k) for k in
                             ("PAGE_TIMEOUT_MS", "DELAY_BETWEEN_PAGES_S", "MAX_SCROLL_ROUNDS",
                              "STABLE_ROUNDS_TO_STOP", "MAX_RETRIES")},
                "pages": []}
    log.info("run %s: %d category pages", run_id, len(jobs))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="vi-VN")  # default Playwright user agent, no disguise
        try:
            for index, (store, group, slug) in enumerate(jobs, 1):
                url = category_url(store, slug, sources)
                if not is_allowed(robots[store], url):
                    log.warning("SKIP (robots.txt disallows) %s", url)
                    manifest["pages"].append({"store": store, "category_slug": slug, "url": url,
                                              "status": "skipped_robots"})
                    continue
                for attempt in range(settings.MAX_RETRIES + 1):
                    record = scrape_page(context, store, group, slug, url, run_id)
                    record["attempt"] = attempt + 1
                    if record["status"] == "ok" or attempt == settings.MAX_RETRIES:
                        break
                    log.warning("retry %s after: %s", url, record["error"] or record["status"])
                    time.sleep(settings.DELAY_BETWEEN_PAGES_S * 2)
                file_name = f"{store}__{slug}.json"
                if previous and (out_dir / file_name).exists():  # keep the earlier attempt as evidence
                    (out_dir / file_name).rename(out_dir / f"{file_name}.replaced_{settings.now_vn():%H%M%S}")
                (out_dir / file_name).write_text(json.dumps(record, ensure_ascii=False, indent=1),
                                                 encoding="utf-8")
                summary = {"store": store, "group": group, "category_slug": slug, "url": url,
                           "file": file_name, "status": record["status"], "error": record["error"],
                           "dom_cards": len(record["dom_cards"]), "responses": len(record["responses"]),
                           "end_reached": record.get("end_reached"), "site_total_count": record.get("site_total_count"),
                           "collected_at": record.get("collected_at")}
                manifest["pages"].append(summary)
                log.info("[%d/%d] %s %s -> %s, %d cards, %d json responses, end_reached=%s %s", index, len(jobs), store,
                         slug, record["status"], summary["dom_cards"], summary["responses"], record.get("end_reached"),
                         record["error"] or "")
                time.sleep(settings.DELAY_BETWEEN_PAGES_S)
        finally:
            browser.close()

    if previous:  # merge: replaced pages get the new result, the run keeps its original start time
        redone = {(pg["store"], pg["category_slug"]): pg for pg in manifest["pages"]}
        previous.setdefault("recollected", []).append(
            {"at": settings.now_vn().isoformat(timespec="seconds"), "pages": [f"{s}/{c}" for s, c in redone]})
        known = {(pg["store"], pg["category_slug"]) for pg in previous["pages"]}
        previous["pages"] = [redone.get((pg["store"], pg["category_slug"]), pg) for pg in previous["pages"]]
        previous["pages"] += [pg for k, pg in redone.items() if k not in known]   # newly added pages
        manifest = previous
    manifest["finished_at"] = settings.now_vn().isoformat(timespec="seconds")
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                                           encoding="utf-8")
    ok = sum(1 for pg in manifest["pages"] if pg["status"] == "ok")
    log.info("run %s finished: %d/%d pages ok -> %s", run_id, ok, len(manifest["pages"]), out_dir)
    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect raw product data (BHX + WinMart)")
    parser.add_argument("--groups", nargs="*", help="only these groups from report2_sources.json")
    parser.add_argument("--max-pages", type=int, help="limit number of category pages (for testing)")
    parser.add_argument("--run-id", help="custom run id (default run_YYYYMMDD_HHMM)")
    parser.add_argument("--only", nargs="*", help="re-collect only these pages, e.g. winmart/cham-soc-ca-nhan--c11")
    args = parser.parse_args()
    setup_logging()
    run(args.groups, args.max_pages, args.run_id, args.only)


if __name__ == "__main__":
    main()
