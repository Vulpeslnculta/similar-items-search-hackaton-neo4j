"""Batch similarity over the whole catalog. Re-run after each ingest.

1. SAME_PRODUCT  - listings sharing a valid GTIN, or the same manufacturer + model
2. SIMILAR       - GDS weighted Node Similarity, computed *within each department* (a jacket is never
                   "similar" to a frying pan because both are black). Shared model/brand/category/spec
                   nodes count by their weight (vocab.SPEC_WEIGHTS / REL_WEIGHTS), so a shared brand
                   matters more than a shared size.
"""
import time

from common import get_driver

SAME_BY_GTIN = """
MATCH (a:Listing) WHERE a.gtin IS NOT NULL
MATCH (b:Listing {gtin: a.gtin}) WHERE elementId(a) < elementId(b)
MERGE (a)-[r:SAME_PRODUCT]->(b) SET r.byGtin = true
RETURN count(r) AS n
"""

SAME_BY_MODEL = """
MATCH (a:Listing)-[:OF_MODEL]->(m:Model)<-[:OF_MODEL]-(b:Listing)
WHERE elementId(a) < elementId(b) AND NOT m.key STARTS WITH '?:'
MERGE (a)-[r:SAME_PRODUCT]->(b) SET r.byModel = true
RETURN count(r) AS n
"""

PROJECT = """
MATCH (l:Listing {department: $dept})-[r:OF_MODEL|MADE_BY|IN_CATEGORY|HAS_SPEC]->(f)
RETURN gds.graph.project($graph, l, f, {relationshipProperties: {w: coalesce(r.w, 1.0)}}) AS g
"""

SIMILARITY = """
CALL gds.nodeSimilarity.write($graph, {
  writeRelationshipType: 'SIMILAR', writeProperty: 'score',
  relationshipWeightProperty: 'w', topK: $topK, similarityCutoff: $cutoff })
YIELD relationshipsWritten RETURN relationshipsWritten
"""


def drop(driver, graph):
    driver.execute_query("CALL gds.graph.drop($g, false) YIELD graphName RETURN graphName", g=graph)


def run_gds(driver, top_k=10, cutoff=0.15):
    with driver.session() as session:  # IN TRANSACTIONS needs an auto-commit transaction
        session.run("MATCH ()-[s:SIMILAR]->() CALL { WITH s DELETE s } IN TRANSACTIONS OF 10000 ROWS").consume()
    depts = driver.execute_query("MATCH (l:Listing) WHERE l.department IS NOT NULL "
                                 "RETURN l.department AS d, count(*) AS n ORDER BY n DESC").records
    total = 0
    for rec in depts:
        if rec["n"] < 2:
            continue
        graph = "features"
        drop(driver, graph)
        driver.execute_query(PROJECT, dept=rec["d"], graph=graph)
        try:
            n = driver.execute_query(SIMILARITY, graph=graph, topK=top_k, cutoff=cutoff).records[0][0]
        finally:
            drop(driver, graph)
        total += n
        print(f"  {rec['d']:24} {rec['n']:6} listings -> {n} SIMILAR links")
    print(f"SIMILAR: {total} relationships (weighted Jaccard within department, cutoff {cutoff}, top {top_k})")


if __name__ == "__main__":
    t = time.time()
    with get_driver() as driver:
        n1 = driver.execute_query(SAME_BY_GTIN).records[0]["n"]
        n2 = driver.execute_query(SAME_BY_MODEL).records[0]["n"]
        print(f"SAME_PRODUCT: {n1} via GTIN, {n2} via manufacturer+model")
        try:
            run_gds(driver)
        except Exception as e:
            print(f"GDS step skipped ({e}). Is the graph-data-science plugin installed?")
    print(f"done in {time.time() - t:.0f}s")
