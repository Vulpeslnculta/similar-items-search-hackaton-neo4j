"""Creates constraints, indexes and the vector index. Safe to re-run."""
from common import get_driver

EMBEDDING_DIMS = 384  # paraphrase-multilingual-MiniLM-L12-v2 (see ingest.py)

STATEMENTS = [
    "CREATE CONSTRAINT listing_url IF NOT EXISTS FOR (l:Listing) REQUIRE l.url IS UNIQUE",
    "CREATE CONSTRAINT mfr_name IF NOT EXISTS FOR (m:Manufacturer) REQUIRE m.name IS UNIQUE",
    "CREATE CONSTRAINT model_key IF NOT EXISTS FOR (m:Model) REQUIRE m.key IS UNIQUE",
    "CREATE CONSTRAINT category_name IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE",
    "CREATE CONSTRAINT source_domain IF NOT EXISTS FOR (s:Source) REQUIRE s.domain IS UNIQUE",
    "CREATE CONSTRAINT spec_kv IF NOT EXISTS FOR (s:Spec) REQUIRE (s.key, s.value) IS UNIQUE",
    "CREATE CONSTRAINT department_name IF NOT EXISTS FOR (d:Department) REQUIRE d.name IS UNIQUE",
    "CREATE INDEX listing_gtin IF NOT EXISTS FOR (l:Listing) ON (l.gtin)",
    "CREATE INDEX listing_department IF NOT EXISTS FOR (l:Listing) ON (l.department)",
    "CREATE INDEX listing_price_eur IF NOT EXISTS FOR (l:Listing) ON (l.priceEur)",
    "CREATE INDEX listing_file IF NOT EXISTS FOR (l:Listing) ON (l.file)",
    "CREATE INDEX listing_price IF NOT EXISTS FOR (l:Listing) ON (l.price)",
    f"""CREATE VECTOR INDEX listing_embedding IF NOT EXISTS FOR (l:Listing) ON l.embedding
        OPTIONS {{indexConfig: {{`vector.dimensions`: {EMBEDDING_DIMS},
                                 `vector.similarity_function`: 'cosine'}}}}""",
]

if __name__ == "__main__":
    with get_driver() as driver:
        for stmt in STATEMENTS:
            driver.execute_query(stmt)
            print("✓", stmt.split("IF NOT EXISTS")[0].strip())
    print("Schema ready.")
