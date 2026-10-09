"""Fetch listing pages from a CSV of URLs into a local cache - polite and resumable.

Usage:
    python crawl.py links.csv              # fetch every URL not fetched yet
    python crawl.py links.csv --pilot      # small representative sample first (~150 URLs)
    python crawl.py links.csv --retry      # also retry URLs that previously errored / were blocked
    python crawl.py --stats                # status summary (overall and per domain)

Politeness:
  - robots.txt is respected; its Crawl-delay is honoured (domains asking for > MAX_DELAY are skipped)
  - one request at a time per domain, at least MIN_DELAY seconds apart; many domains in parallel
  - a domain that keeps blocking us (403/429/bot-check) is abandoned after BLOCK_LIMIT hits in a row

Pages are stored gzipped in cache/pages/<domain>/<sha1>.html.gz; status per URL in cache/crawl.sqlite.
`python ingest.py --from-cache` then loads every successfully fetched page into Neo4j.
"""
import argparse
import csv
import gzip
import hashlib
import random
import sqlite3
import sys
import threading
import time
import urllib.robotparser
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

from extraction import BLOCK_PAGE, has_product_signals

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "cache"
PAGES = CACHE / "pages"
DB_PATH = CACHE / "crawl.sqlite"

MIN_DELAY = 1.5        # seconds between requests to the same domain
MAX_DELAY = 30         # robots Crawl-delay above this -> skip the domain
WORKERS = 24           # domains fetched in parallel
TIMEOUT = 25
MAX_BYTES = 15_000_000
BLOCK_LIMIT = 5        # consecutive blocked responses before giving up on a domain
RETRYABLE = {429, 500, 502, 503, 504}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/128.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "da,en;q=0.8,sv;q=0.6,nb;q=0.6,de;q=0.5",
}

# Final statuses are not retried; the rest are retried with --retry.
FINAL = {"ok", "not_found", "robots", "not_html", "too_large"}
# needs_js: static HTML has no product data (JavaScript-rendered site) -> handled by `--render`.
JS_PROBE = 3  # if a domain's first N pages all need JS, its remaining URLs skip the static fetch

_db_lock = threading.Lock()


def domain_of(url):
    return urlparse(url).netloc.lower().removeprefix("www.")


def open_db():
    CACHE.mkdir(exist_ok=True)
    db = sqlite3.connect(DB_PATH, check_same_thread=False)
    db.execute("""CREATE TABLE IF NOT EXISTS pages (
        url TEXT PRIMARY KEY, domain TEXT, status TEXT, http_code INTEGER, path TEXT,
        final_url TEXT, encoding TEXT, error TEXT, fetched_at TEXT)""")
    db.execute("CREATE INDEX IF NOT EXISTS pages_status ON pages(status)")
    return db


def record(db, url, status, http_code=None, path=None, final_url=None, encoding=None, error=None):
    with _db_lock:
        db.execute("INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?,?,?,?)",
                   (url, domain_of(url), status, http_code, path, final_url, encoding,
                    (error or "")[:300] or None, datetime.now(timezone.utc).isoformat(timespec="seconds")))
        db.commit()


def read_urls(csv_path):
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        sample = f.read(4096)
        f.seek(0)
        has_header = not sample.lstrip().lower().startswith("http")
        rows = csv.reader(f)
        if has_header:
            header = [h.strip().lower() for h in next(rows)]
            col = next((i for i, h in enumerate(header) if h in ("url", "link", "href")), 0)
        else:
            col = 0
        seen, urls = set(), []
        for row in rows:
            if len(row) > col and (u := row[col].strip()).startswith("http") and u not in seen:
                seen.add(u)
                urls.append(u)
    return urls


def pilot_sample(urls, top_domains=25, per_domain=3, tail=75, seed=7):
    by_domain = defaultdict(list)
    for u in urls:
        by_domain[domain_of(u)].append(u)
    ranked = sorted(by_domain, key=lambda d: -len(by_domain[d]))
    rng = random.Random(seed)
    picked = [u for d in ranked[:top_domains] for u in rng.sample(by_domain[d], min(per_domain, len(by_domain[d])))]
    rest = [u for d in ranked[top_domains:] for u in by_domain[d]]
    return picked + rng.sample(rest, min(tail, len(rest)))


def load_robots(session, sample_url):
    parsed = urlparse(sample_url)
    rp = urllib.robotparser.RobotFileParser()
    try:
        r = session.get(f"{parsed.scheme}://{parsed.netloc}/robots.txt", timeout=10)
        if r.status_code >= 400 or "html" in r.headers.get("content-type", ""):
            rp.parse([])  # no robots.txt -> everything allowed
        else:
            rp.parse(r.text.splitlines())
    except requests.RequestException:
        rp.parse([])
    return rp


def fetch(session, url):
    """Returns (status, http_code, body_bytes, final_url, encoding, error)."""
    for attempt in range(3):
        try:
            r = session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True)
            try:
                body = r.raw.read(MAX_BYTES + 1, decode_content=True)
            finally:
                r.close()
        except Exception as e:  # network errors, broken gzip streams, etc.
            if attempt == 2:
                return "error", None, None, None, None, type(e).__name__
            time.sleep(5 * (attempt + 1))
            continue
        code = r.status_code
        if code in RETRYABLE and attempt < 2:
            retry_after = r.headers.get("Retry-After", "")
            time.sleep(min(int(retry_after), 60) if retry_after.isdigit() else 10 * (attempt + 1))
            continue
        if code in (404, 410):
            return "not_found", code, None, r.url, None, None
        if code in (401, 403, 429) or code == 503:
            return "blocked", code, None, r.url, None, None
        if code >= 400:
            return "http_error", code, None, r.url, None, None
        if len(body) > MAX_BYTES:
            return "too_large", code, None, r.url, None, None
        if "html" not in r.headers.get("content-type", "html"):
            return "not_html", code, None, r.url, None, None
        enc = r.encoding if r.encoding and r.encoding.lower() != "iso-8859-1" else (r.apparent_encoding or "utf-8")
        head = body[:20000].decode(enc, errors="ignore")
        title = head.split("<title", 1)[1].split("</title>", 1)[0] if "<title" in head else ""
        if (BLOCK_PAGE.search(title) and "ld+json" not in head) or \
                any(k in r.url.lower() for k in ("/challenge", "captcha", "/risk/")):
            return "blocked", code, None, r.url, enc, "bot-check page"
        if not has_product_signals(body.decode(enc, errors="ignore")):
            return "needs_js", code, body, r.url, enc, "no product data in static HTML"
        return "ok", code, body, r.url, enc, None
    return "error", None, None, None, None, "retries exhausted"


def crawl_domain(db, domain, urls, progress):
    session = requests.Session()
    session.headers.update(HEADERS)
    rp = load_robots(session, urls[0])
    delay = max(MIN_DELAY, float(rp.crawl_delay("*") or 0))
    if delay > MAX_DELAY:
        for u in urls:
            record(db, u, "robots", error=f"crawl-delay {delay}s")
        progress(len(urls))
        return
    blocked_in_row = 0
    js_probe = []  # statuses of the first JS_PROBE fetched pages
    for i, url in enumerate(urls):
        if not rp.can_fetch(HEADERS["User-Agent"], url):
            record(db, url, "robots")
            progress(1)
            continue
        if blocked_in_row >= BLOCK_LIMIT:
            record(db, url, "skipped", error="domain keeps blocking")
            progress(1)
            continue
        if len(js_probe) >= JS_PROBE and all(st == "needs_js" for st in js_probe[:JS_PROBE]):
            record(db, url, "needs_js", error="domain renders with JavaScript (not fetched statically)")
            progress(1)
            continue
        started = time.monotonic()
        status, code, body, final_url, enc, err = fetch(session, url)
        path = None
        if status in ("ok", "needs_js"):
            js_probe.append(status)
        if body is not None and status in ("ok", "needs_js"):
            path = PAGES / domain / (hashlib.sha1(url.encode()).hexdigest() + ".html.gz")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(gzip.compress(body, compresslevel=6))
            path = str(path.relative_to(CACHE))
        blocked_in_row = blocked_in_row + 1 if status == "blocked" else 0
        record(db, url, status, code, path, final_url, enc, err)
        progress(1)
        if i < len(urls) - 1:
            time.sleep(max(0.0, delay - (time.monotonic() - started)))


def print_stats(db, top=25):
    total = db.execute("SELECT count(*) FROM pages").fetchone()[0]
    print(f"{total} URLs recorded")
    for status, n in db.execute("SELECT status, count(*) FROM pages GROUP BY status ORDER BY 2 DESC"):
        print(f"  {status:12} {n:6}  ({n / max(total, 1):.0%})")
    print(f"\nTop domains (ok / total):")
    for d, ok, n, statuses in db.execute("""
            SELECT domain, sum(status='ok'), count(*), group_concat(DISTINCT status)
            FROM pages GROUP BY domain ORDER BY count(*) DESC LIMIT ?""", (top,)):
        print(f"  {d:30} {ok:5} / {n:<5} {statuses}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="?", help="CSV with a 'url' column (or URLs in the first column)")
    ap.add_argument("--pilot", action="store_true", help="fetch a ~150 URL representative sample")
    ap.add_argument("--retry", action="store_true", help="retry non-final statuses (error, blocked, skipped…)")
    ap.add_argument("--stats", action="store_true", help="print status summary and exit")
    ap.add_argument("--workers", type=int, default=WORKERS)
    a = ap.parse_args()

    db = open_db()
    if a.stats or not a.csv:
        print_stats(db)
        return

    urls = read_urls(a.csv)
    if a.pilot:
        urls = pilot_sample(urls)
    done = {u: s for u, s in db.execute("SELECT url, status FROM pages")}
    todo = [u for u in urls if u not in done or (a.retry and done[u] not in FINAL)]
    print(f"{len(urls)} URLs in scope, {len(urls) - len(todo)} already done, {len(todo)} to fetch")
    if not todo:
        print_stats(db)
        return

    by_domain = defaultdict(list)
    for u in todo:
        by_domain[domain_of(u)].append(u)
    # biggest domains first so the long ones don't start last
    domains = sorted(by_domain, key=lambda d: -len(by_domain[d]))

    count, lock, started = [0], threading.Lock(), time.monotonic()

    def progress(n):
        with lock:
            count[0] += n
            if count[0] % 50 == 0 or count[0] == len(todo):
                rate = count[0] / max(time.monotonic() - started, 1e-6)
                print(f"  {count[0]}/{len(todo)}  ({rate:.1f} pages/s)", flush=True)

    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        futures = [pool.submit(crawl_domain, db, d, by_domain[d], progress) for d in domains]
        for f in as_completed(futures):
            if exc := f.exception():
                print(f"worker error: {exc!r}", file=sys.stderr)
    print()
    print_stats(db)


if __name__ == "__main__":
    main()
