"""Find listings similar to a given one.

Usage:
    python similar.py <url-or-html-file> [--mode hybrid|same|gds] [--in-stock] [--any-department] [--limit 10]

Modes:
    hybrid (default)  vector search for candidates, re-ranked by shared weighted attributes + price closeness
    same              the same product in other shops (price comparison in EUR)
    gds               precomputed SIMILAR relationships (run compute_similarity.py first)
Results stay within the listing's department unless --any-department is given.
"""
import argparse

from common import get_driver, to_url

# Tune these to your data. Shared attributes count by their stored weight (vocab.SPEC_WEIGHTS / REL_WEIGHTS).
W_TEXT, W_PRICE = 4.0, 2.0

FIND = "MATCH (x:Listing) WHERE x.url = $url OR x.file = $url RETURN x LIMIT 1"

HYBRID = """
MATCH (x:Listing) WHERE elementId(x) = $id
CALL db.index.vector.queryNodes('listing_embedding', $candidates, x.embedding)
  YIELD node AS y, score AS textScore
WHERE y <> x AND ($anyDept OR y.department = x.department)
  AND (NOT $inStock OR y.availability = 'InStock')
OPTIONAL MATCH (x)-[r1:OF_MODEL|MADE_BY|IN_CATEGORY|HAS_SPEC]->(f)<-[r2]-(y)
  WHERE type(r1) = type(r2)
WITH x, y, textScore, sum(coalesce(r1.w, 0.0)) AS attrScore,
     collect(DISTINCT CASE WHEN f:Spec THEN f.key + '=' + f.value
                           WHEN f IS NOT NULL THEN toLower(labels(f)[0]) + '=' + coalesce(f.name, '') END) AS shared
WITH y, textScore, attrScore, shared,
     CASE WHEN x.priceEur > 0 AND y.priceEur > 0
          THEN CASE WHEN x.priceEur < y.priceEur THEN x.priceEur / y.priceEur ELSE y.priceEur / x.priceEur END
          ELSE 0.0 END AS priceScore
OPTIONAL MATCH (y)-[:LISTED_ON]->(s:Source)
RETURN y.title AS title, s.domain AS shop, y.price AS price, y.currency AS currency, y.priceEur AS eur,
       y.availability AS availability, y.condition AS condition, y.department AS department, shared,
       round($wText * textScore + attrScore + $wPrice * priceScore, 2) AS score
ORDER BY score DESC LIMIT $limit
"""

SAME = """
MATCH (x:Listing)-[:SAME_PRODUCT]-(y:Listing)
WHERE elementId(x) = $id AND (NOT $inStock OR y.availability = 'InStock')
OPTIONAL MATCH (y)-[:LISTED_ON]->(s:Source)
RETURN DISTINCT y.title AS title, s.domain AS shop, y.price AS price, y.currency AS currency, y.priceEur AS eur,
       y.availability AS availability, y.condition AS condition, y.department AS department
ORDER BY eur LIMIT $limit
"""

GDS = """
MATCH (x:Listing)-[r:SIMILAR]->(y:Listing)
WHERE elementId(x) = $id AND (NOT $inStock OR y.availability = 'InStock')
OPTIONAL MATCH (y)-[:LISTED_ON]->(s:Source)
RETURN y.title AS title, s.domain AS shop, y.price AS price, y.currency AS currency, y.priceEur AS eur,
       y.availability AS availability, y.condition AS condition, y.department AS department,
       round(r.score, 3) AS score
ORDER BY score DESC LIMIT $limit
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("listing", help="URL or local HTML file that was ingested")
    ap.add_argument("--mode", choices=["hybrid", "same", "gds"], default="hybrid")
    ap.add_argument("--in-stock", action="store_true", help="only show InStock listings")
    ap.add_argument("--any-department", action="store_true", help="don't restrict to the same department")
    ap.add_argument("--limit", type=int, default=10)
    a = ap.parse_args()

    url = to_url(a.listing)
    with get_driver() as driver:
        found = driver.execute_query(FIND, url=url).records
        if not found:
            raise SystemExit(f"Listing not found: {url}\nIngest it first: python ingest.py {a.listing}")
        x = found[0]["x"]
        print(f"Similar to: {x.get('title')}  ({x.get('price')} {x.get('currency')}, {x.get('priceEur')} EUR)"
              f"  [{x.get('department')}]  [mode: {a.mode}]\n")

        query = {"hybrid": HYBRID, "same": SAME, "gds": GDS}[a.mode]
        records = driver.execute_query(
            query, id=x.element_id, inStock=a.in_stock, anyDept=a.any_department, limit=a.limit,
            candidates=max(100, a.limit * 10), wText=W_TEXT, wPrice=W_PRICE).records
        if not records:
            print({"same": "No other shop lists this exact product (same GTIN or manufacturer+model).",
                   "gds": "No SIMILAR links - run compute_similarity.py after ingesting.",
                   "hybrid": "No matches."}[a.mode])
        for r in records:
            score = f"{r['score']:>6}  " if "score" in r.keys() else ""
            print(f"{score}{(r['title'] or '')[:55]:55} | {r['shop']} | {r['price']} {r['currency']} "
                  f"(€{r['eur']}) | {r['availability']} | {r['condition'] or ''}")
            if r.get("shared"):
                print(f"        shared: {', '.join(r['shared'])}")


if __name__ == "__main__":
    main()
