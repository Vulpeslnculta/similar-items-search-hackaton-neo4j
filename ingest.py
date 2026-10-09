"""Load listing pages into Neo4j: extract -> normalize -> classify -> embed -> write (batched).

Usage:
    python ingest.py --from-cache           # pages downloaded/rendered by crawl.py/render.py, not ingested yet
    python ingest.py --from-cache --all     # re-ingest every cached page (after improving vocab/extraction)
    python ingest.py page.html samples/ https://shop.example/item/1     # ad-hoc files, folders, URLs

Incremental: each cached page is ingested once (tracked in cache/crawl.sqlite, table `ingested`), so this
can run repeatedly while crawl.py / render.py are still working.
"""
import argparse
import gzip
import sqlite3
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

from common import get_driver, to_url
from extraction import BlockedPage, decode_html, extract
from normalize import BrandIndex, DepartmentClassifier, DepartmentModel, load_fx, norm_brand, normalize
from vocab import REL_WEIGHTS

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"  # multilingual, 384-dim (matches the vector index)
CACHE = Path(__file__).resolve().parent / "cache"
BATCH = 250
WORKERS = 8

UPSERT = """
UNWIND $rows AS row
MERGE (l:Listing {url: row.url})
WITH l, row
OPTIONAL MATCH (l)-[old:MADE_BY|OF_MODEL|IN_CATEGORY|HAS_SPEC|LISTED_ON|IN_DEPARTMENT]->()
DELETE old
WITH DISTINCT l, row
SET l.title = row.title, l.description = row.description, l.price = row.price, l.currency = row.currency,
    l.priceEur = row.price_eur, l.availability = row.availability, l.condition = row.condition,
    l.gtin = row.gtin, l.file = row.file, l.department = row.department, l.deptMethod = row.dept_method,
    l.deptConfidence = row.dept_conf, l.categoryPath = row.category_path, l.embedding = row.embedding,
    l.updatedAt = datetime()
MERGE (s:Source {domain: row.source})
MERGE (l)-[:LISTED_ON]->(s)
MERGE (d:Department {name: row.department})
MERGE (l)-[:IN_DEPARTMENT]->(d)
FOREACH (_ IN CASE WHEN row.manufacturer IS NULL THEN [] ELSE [1] END |
  MERGE (m:Manufacturer {name: row.manufacturer})
  MERGE (l)-[r:MADE_BY]->(m) SET r.w = $w.MADE_BY)
FOREACH (_ IN CASE WHEN row.model IS NULL THEN [] ELSE [1] END |
  MERGE (md:Model {key: coalesce(row.manufacturer, '?') + ':' + row.model})
  SET md.name = row.model
  MERGE (l)-[r:OF_MODEL]->(md) SET r.w = $w.OF_MODEL)
FOREACH (_ IN CASE WHEN row.category IS NULL THEN [] ELSE [1] END |
  MERGE (c:Category {name: row.category})
  MERGE (l)-[r:IN_CATEGORY]->(c) SET r.w = $w.IN_CATEGORY
  MERGE (c)-[:PART_OF]->(d))
FOREACH (spec IN row.specs |
  MERGE (a:Spec {key: spec.key, value: spec.value})
  SET a.num = spec.num, a.unit = spec.unit
  MERGE (l)-[r:HAS_SPEC]->(a) SET r.w = spec.w)
"""

# A listing previously stored under its file URL is replaced by the canonical-URL version.
DROP_STALE = """
UNWIND $pairs AS p
MATCH (stale:Listing {url: p.file}) WHERE p.file <> p.url
DETACH DELETE stale
"""

DROP_ORPHANS = """
MATCH (n) WHERE (n:Source OR n:Manufacturer OR n:Model OR n:Category OR n:Spec OR n:Department)
  AND NOT (n)<--()
DETACH DELETE n
"""


# ---------- sources ----------

def cache_db():
    db = sqlite3.connect(CACHE / "crawl.sqlite", timeout=60)
    db.execute("CREATE TABLE IF NOT EXISTS ingested (url TEXT PRIMARY KEY, listing_url TEXT, status TEXT, at TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS renders (url TEXT PRIMARY KEY, domain TEXT, status TEXT, "
               "http_code INTEGER, path TEXT, error TEXT, rendered_at TEXT)")
    db.commit()
    return db


def cached_pages(db, everything):
    """(url, cache path) for every page with usable HTML; the rendered version wins over the static one."""
    rows = db.execute("""
        SELECT p.url, COALESCE(CASE WHEN r.status IN ('ok', 'no_product') THEN r.path END,
                               CASE WHEN p.status IN ('ok', 'needs_js') THEN p.path END) AS path,
               r.status AS render_status, p.status
        FROM pages p LEFT JOIN renders r ON r.url = p.url
        WHERE p.status IN ('ok', 'needs_js')""").fetchall()
    done = set() if everything else {u for (u,) in db.execute("SELECT url FROM ingested")}
    out = []
    for url, path, render_status, status in rows:
        if url in done or not path:
            continue
        if status == "needs_js" and render_status is None:
            continue  # wait for render.py (the static HTML has no product data)
        out.append((url, str(CACHE / path)))
    return out


def adhoc_sources(args):
    for a in args:
        p = Path(a)
        if p.is_dir():
            yield from ((to_url(str(f)), str(f)) for f in sorted(p.rglob("*")) if f.suffix.lower() in (".html", ".htm"))
        elif a.startswith(("http://", "https://")):
            yield a, a
        else:
            yield to_url(a), a


def load_and_extract(item):
    """Runs in a worker process. -> (url, record | None, status)."""
    url, src = item
    try:
        if src.startswith(("http://", "https://")):
            r = requests.get(src, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
            r.raise_for_status()
            html = r.text
        else:
            raw = Path(src).read_bytes()
            html = decode_html(gzip.decompress(raw) if src.endswith(".gz") else raw)
        rec = extract(html, url)
        if not rec["title"] and not rec["price_raw"]:
            return url, None, "empty"
        return url, rec, "ok"
    except BlockedPage:
        return url, None, "blocked"
    except Exception as e:
        return url, None, f"error: {type(e).__name__}: {str(e)[:100]}"


# ---------- pipeline ----------

def run(items, mark_ingested=None):
    t0 = time.time()
    print(f"extracting {len(items)} pages with {WORKERS} processes...", flush=True)
    with ProcessPoolExecutor(WORKERS) as ex:
        results = list(ex.map(load_and_extract, items, chunksize=8))
    recs = [(u, r) for u, r, st in results if r]
    failed = [(u, st) for u, r, st in results if not r]
    print(f"  {len(recs)} extracted, {len(failed)} without product data ({time.time() - t0:.0f}s)")
    for u, st in failed[:5]:
        print(f"    {st:30} {u[:90]}")
    if not recs:
        if mark_ingested:
            mark_ingested([(u, None, st) for u, st in failed])
        return

    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer(EMBEDDING_MODEL)
    fx = load_fx()
    with get_driver() as driver:
        # brands known anywhere in the catalog help infer missing ones from titles/URLs
        brands = BrandIndex()
        for rec in driver.execute_query("MATCH (m:Manufacturer)<-[:MADE_BY]-(l) "
                                        "RETURN m.name AS b, count(l) AS n").records:
            brands.add(rec["b"], rec["n"])
        for _, r in recs:
            brands.add(norm_brand(r["brand_raw"]))

        # departments, step 1: keywords
        kw = DepartmentClassifier()
        labels = [kw.keyword_label(r) for _, r in recs]
        rows = [normalize(r, fx, brands, dept or "other") for (_, r), (dept, _) in zip(recs, labels)]

        t1 = time.time()
        vecs = embedder.encode([row["embed_text"] for row in rows], batch_size=64, normalize_embeddings=True,
                               show_progress_bar=len(rows) > 500)
        print(f"  embedded {len(rows)} listings ({time.time() - t1:.0f}s)")

        # departments, step 2: classifier trained on confident keyword labels (this batch + catalog)
        X = [vecs[i] for i, (d, clear) in enumerate(labels) if clear]
        y = [d for d, clear in labels if clear]
        if len(X) < 3000:
            for rec in driver.execute_query(
                    "MATCH (l:Listing) WHERE l.deptMethod = 'keywords' AND l.embedding IS NOT NULL "
                    "RETURN l.embedding AS e, l.department AS d LIMIT 20000").records:
                X.append(rec["e"])
                y.append(rec["d"])
        unlabeled = [i for i, (d, _) in enumerate(labels) if d is None]
        model_preds = DepartmentModel().fit(X, y).predict([vecs[i] for i in unlabeled]) if unlabeled else []
        final = {i: (d, "keywords", 1.0) for i, (d, _) in enumerate(labels) if d}
        for i, (d, conf) in zip(unlabeled, model_preds):
            final[i] = (d, "model" if d != "other" else "none", round(conf, 3))

        for i, row in enumerate(rows):
            dept, method, conf = final[i]
            if dept != row["department"]:  # gender/model inference depend on the department
                row.update(normalize(recs[i][1], fx, brands, dept))
            row.update(department=dept, dept_method=method, dept_conf=conf, embedding=vecs[i].tolist())
            row.pop("embed_text", None)

        t2 = time.time()
        stale = [{"url": r["url"], "file": r["file"]} for r in rows if r.get("file")]
        if stale:
            driver.execute_query(DROP_STALE, pairs=stale)
        for start in range(0, len(rows), BATCH):
            driver.execute_query(UPSERT, rows=rows[start:start + BATCH], w=REL_WEIGHTS)
            print(f"  wrote {min(start + BATCH, len(rows))}/{len(rows)}", end="\r", flush=True)
        pruned = prune_missing_files(driver)
        driver.execute_query(DROP_ORPHANS)
        print(f"  wrote {len(rows)} listings to Neo4j ({time.time() - t2:.0f}s)"
              + (f", removed {pruned} whose file is gone" if pruned else ""))

    if mark_ingested:
        mark_ingested([(u, row["url"], "ok") for (u, _), row in zip(recs, rows)] +
                      [(u, None, st) for u, st in failed])

    from collections import Counter
    methods = Counter(final[i][1] for i in final)
    print(f"\ndepartments: {dict(Counter(r['department'] for r in rows).most_common())}")
    print(f"department decided by: {dict(methods)}")
    cov = {f: f"{sum(1 for r in rows if r[f]) / len(rows):.0%}"
           for f in ("manufacturer", "model", "gtin", "category", "price_eur")}
    print(f"coverage: {cov}, with specs: {sum(1 for r in rows if r['specs']) / len(rows):.0%}")
    print(f"done in {time.time() - t0:.0f}s. Next: python compute_similarity.py")


def prune_missing_files(driver):
    """Listings ingested from local files that were since deleted or replaced."""
    recs = driver.execute_query("MATCH (l:Listing) WHERE l.file IS NOT NULL RETURN elementId(l) AS id, l.file AS f").records
    gone = [r["id"] for r in recs if not Path(unquote(urlparse(r["f"]).path)).exists()]
    if gone:
        driver.execute_query("MATCH (l:Listing) WHERE elementId(l) IN $ids DETACH DELETE l", ids=gone)
    return len(gone)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sources", nargs="*", help="HTML files, folders or URLs")
    ap.add_argument("--from-cache", action="store_true", help="ingest pages fetched by crawl.py / render.py")
    ap.add_argument("--all", action="store_true", help="with --from-cache: re-ingest already ingested pages too")
    ap.add_argument("--limit", type=int, help="ingest at most N pages (testing)")
    a = ap.parse_args()

    if a.from_cache:
        db = cache_db()
        items = cached_pages(db, a.all)[:a.limit]
        if not items:
            print("Nothing new to ingest.")
            return

        def mark(entries):
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            db.executemany("INSERT OR REPLACE INTO ingested VALUES (?,?,?,?)", [(u, l, s, now) for u, l, s in entries])
            db.commit()
        run(items, mark)
    elif a.sources:
        run(list(adhoc_sources(a.sources))[:a.limit])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
