"""Render JavaScript-only pages (crawl status `needs_js`) with headless Chromium - async, polite, resumable.

Usage:
    python render.py links.csv          # render pending pages of domains whose static crawl is finished
    python render.py                    # render every pending needs_js page
    python render.py --retry            # also retry earlier render errors / blocks
    python render.py --retry --domain aboutyou.dk --delay 6   # after a rate limit (HTTP 429): slower retry
    python render.py --stats

Runs alongside crawl.py: domains still being fetched statically are left for a later run, so no site
gets parallel requests from both. Same politeness as crawl.py: one tab per domain, >= MIN_DELAY between
pages, CONCURRENCY domains at a time, a domain that keeps blocking is abandoned. Images, fonts and
media are not downloaded. Rendered HTML goes to cache/pages/<domain>/<sha1>.rendered.html.gz.
"""
import argparse
import asyncio
import gzip
import hashlib
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

from crawl import CACHE, DB_PATH, HEADERS, MIN_DELAY, PAGES, domain_of, read_urls
from extraction import BLOCK_PAGE, has_product_signals

CONCURRENCY = 6          # domains rendered in parallel
NAV_TIMEOUT = 30_000     # ms
SIGNAL_WAIT = 10_000     # ms to wait for product data after DOMContentLoaded
BLOCK_LIMIT = 5
FINAL = {"ok", "no_product", "not_found"}

PRODUCT_READY_JS = """() => {
  const ld = [...document.querySelectorAll('script[type="application/ld+json"]')].map(s => s.textContent).join(' ');
  return /"Product(Group)?"/.test(ld) ||
         !!document.querySelector('meta[property="product:price:amount"], [itemprop="price"]');
}"""


def open_db():
    db = sqlite3.connect(DB_PATH, timeout=60)
    db.execute("""CREATE TABLE IF NOT EXISTS renders (
        url TEXT PRIMARY KEY, domain TEXT, status TEXT, http_code INTEGER, path TEXT, error TEXT, rendered_at TEXT)""")
    db.commit()
    return db


def record(db, url, status, code=None, path=None, error=None):
    db.execute("INSERT OR REPLACE INTO renders VALUES (?,?,?,?,?,?,?)",
               (url, domain_of(url), status, code, path, (error or "")[:300] or None,
                datetime.now(timezone.utc).isoformat(timespec="seconds")))
    db.commit()


def pending(db, csv_path, retry, domains=None):
    done = {u: s for u, s in db.execute("SELECT url, status FROM renders")}
    rows = db.execute("SELECT url, domain FROM pages WHERE status = 'needs_js'").fetchall()
    todo = [(u, d) for u, d in rows if (u not in done or (retry and done[u] not in FINAL))
            and (not domains or d in domains)]
    if csv_path:  # leave domains the static crawler hasn't finished yet
        fetched = {u for (u,) in db.execute("SELECT url FROM pages")}
        unfinished = {domain_of(u) for u in read_urls(csv_path) if u not in fetched}
        todo = [(u, d) for u, d in todo if d not in unfinished]
    by_domain = defaultdict(list)
    for u, d in todo:
        by_domain[d].append(u)
    return by_domain


async def block_heavy(route):
    if route.request.resource_type in ("image", "media", "font"):
        await route.abort()
    else:
        await route.continue_()


async def render_one(page, domain, url):
    from playwright.async_api import TimeoutError as PlaywrightTimeout
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
        try:
            await page.wait_for_function(PRODUCT_READY_JS, timeout=SIGNAL_WAIT)
        except PlaywrightTimeout:
            pass
        html, title, final_url = await page.content(), await page.title(), page.url
    except Exception as e:
        return "error", None, None, f"{type(e).__name__}: {str(e)[:120]}"
    code = resp.status if resp else None
    if code in (404, 410):
        return "not_found", code, None, None
    if code in (401, 403, 429, 503) or BLOCK_PAGE.search(title or "") or \
            any(k in final_url.lower() for k in ("/challenge", "captcha", "/risk/")):
        return "blocked", code, None, f"http {code}: {title[:60]}"
    path = PAGES / domain / (hashlib.sha1(url.encode()).hexdigest() + ".rendered.html.gz")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(html.encode("utf-8"), compresslevel=6))
    return ("ok" if has_product_signals(html) else "no_product"), code, str(path.relative_to(CACHE)), None


async def render_domain(browser, db, domain, urls, sem, progress, delay):
    async with sem:
        ctx = await browser.new_context(user_agent=HEADERS["User-Agent"], locale="da-DK",
                                        extra_http_headers={"Accept-Language": HEADERS["Accept-Language"]})
        await ctx.route("**/*", block_heavy)
        page = await ctx.new_page()
        blocked = 0
        try:
            for url in urls:
                if blocked >= BLOCK_LIMIT:
                    record(db, url, "skipped", error="domain keeps blocking")
                    progress(domain, "skipped")
                    continue
                started = time.monotonic()
                status, code, path, err = await render_one(page, domain, url)
                blocked = blocked + 1 if status == "blocked" else 0
                record(db, url, status, code, path, err)
                progress(domain, status)
                await asyncio.sleep(max(0.0, delay - (time.monotonic() - started)))
        finally:
            await ctx.close()


async def run(by_domain, concurrency, delay=MIN_DELAY):
    from playwright.async_api import async_playwright
    db = open_db()
    total = sum(len(v) for v in by_domain.values())
    counts, started = defaultdict(int), time.monotonic()

    def progress(domain, status):
        counts[status] += 1
        n = sum(counts.values())
        if n % 25 == 0 or n == total:
            rate = n / max(time.monotonic() - started, 1e-6)
            print(f"  {n}/{total}  {dict(counts)}  ({rate:.1f} pages/s)", flush=True)

    sem = asyncio.Semaphore(concurrency)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            domains = sorted(by_domain, key=lambda d: -len(by_domain[d]))  # big domains start first
            results = await asyncio.gather(*(render_domain(browser, db, d, by_domain[d], sem, progress, delay)
                                             for d in domains), return_exceptions=True)
            for d, r in zip(domains, results):
                if isinstance(r, Exception):
                    print(f"domain {d} failed: {r!r}", file=sys.stderr)
        finally:
            await browser.close()


def print_stats(db):
    for status, n in db.execute("SELECT status, count(*) FROM renders GROUP BY status ORDER BY 2 DESC"):
        print(f"  {status:12} {n:6}")
    print("Top domains (ok / rendered):")
    for d, ok, n in db.execute("""SELECT domain, sum(status IN ('ok','no_product')), count(*) FROM renders
                                  GROUP BY domain ORDER BY count(*) DESC LIMIT 15"""):
        print(f"  {d:30} {ok:5} / {n}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="?", help="the crawl CSV: skip domains the static crawl hasn't finished")
    ap.add_argument("--retry", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--concurrency", type=int, default=CONCURRENCY)
    ap.add_argument("--delay", type=float, default=MIN_DELAY, help="seconds between pages of one domain")
    ap.add_argument("--domain", action="append", help="only these domains (repeatable)")
    a = ap.parse_args()
    db = open_db()
    if a.stats:
        print_stats(db)
        return
    by_domain = pending(db, a.csv, a.retry, set(a.domain or []))
    total = sum(len(v) for v in by_domain.values())
    print(f"{total} pages to render across {len(by_domain)} domains")
    if total:
        asyncio.run(run(by_domain, a.concurrency, max(a.delay, MIN_DELAY)))
    print_stats(db)


if __name__ == "__main__":
    main()
