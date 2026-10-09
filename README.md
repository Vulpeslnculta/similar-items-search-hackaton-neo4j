# neo4j-listings

Ingest product listing pages from any shop into Neo4j, normalize them across categories (clothes,
cameras, computers, cosmetics, …) and languages, and find similar or identical items by
manufacturer, model, category, specs, price and availability.

## Setup

1. **Credentials**: create `password.txt` in this folder (git-ignored):
   - one line: the password (user defaults to `neo4j`), or
   - two lines: username, then password (for an existing/remote Neo4j).
2. **Neo4j** (Docker, with Graph Data Science): `./start_neo4j.sh` → http://localhost:7474.
   To use an existing instance, set `NEO4J_URI` instead.
3. **Python**:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   python -m playwright install chromium     # only needed for JavaScript-rendered shops
   ```
4. **Schema** (safe to re-run): `python setup_schema.py`

## Bulk run from a CSV of URLs (asynchronous)

```bash
./pipeline.sh for_nikodem.csv       # the included dataset: 10,000 product URLs from ~1,500 shops
./pipeline.sh links.csv             # or your own CSV with a `url` column (or URLs in the first column)
```

Try it small first: `python crawl.py for_nikodem.csv --pilot` fetches a ~150 URL representative sample.
A full run of the included CSV takes a few hours (polite per-site pacing) and ~1 GB of `cache/`.

Downloading, rendering and ingesting run **concurrently**: the database fills up while pages are still
being fetched, and similarity is computed at the end. Everything is resumable — re-run the same
command after an interruption. Progress: `cache/crawl.log`, `cache/render.log`, `cache/ingest.log`.

The steps can also be run individually:

| Step | Command | What it does |
|---|---|---|
| download | `python crawl.py links.csv` (`--pilot` for a ~150 URL sample, `--stats`) | Fetches pages into `cache/` (gzipped). Respects robots.txt and Crawl-delay, one request at a time per site (≥ 1.5 s apart), many sites in parallel. Sites that keep blocking are abandoned, not evaded. |
| render | `python render.py links.csv` (`--stats`) | Pages whose HTML has no product data (JavaScript shops) are rendered in headless Chromium — async, several sites at once, same politeness. |
| ingest | `python ingest.py --from-cache` (`--all` to redo everything) | Incremental: only pages not ingested yet. Extraction runs in 8 processes; writes are batched. |
| similarity | `python compute_similarity.py` | `SAME_PRODUCT` + per-department `SIMILAR` links. |

Single files, folders of saved pages, or URLs: `python ingest.py page.html saved_pages/ https://…`
(a one-off URL is fetched without JavaScript rendering — use the pipeline for JavaScript-heavy shops).

## Querying

```bash
python similar.py <url-or-file>                       # hybrid: text embedding + shared attributes + price
python similar.py <url-or-file> --mode same           # same product in other shops, cheapest first (EUR)
python similar.py <url-or-file> --mode gds --in-stock # precomputed weighted-Jaccard neighbours
```

Results stay within the listing's department (`--any-department` to lift that). The listing must
already be ingested; quote URLs and paths. Examples from the included dataset:

```bash
# football boot -> other Nike shoes and football boots
python similar.py "https://classicbootsmatter.com/products/nike-tiempo-legend-iv-sg-pro-black-white-red-509041-010" --limit 6
# the same USB4 cable in another shop, cheapest first
python similar.py "https://www.csmegastore.dk/i/21870841/usb-c-kabel-med-tekstilkappe-usb4-240-w-40-gbit-s-power-delivery-1-8-m-kabellængde-1-8-m" --mode same
# the same mug series in other colours/sizes
python similar.py "https://hjem.dk/shop/2272-krus-uden-hank/76927-ib-laursen-mynte-cafe-latte-krus-20-cl-green-tea/" --mode gds --limit 6
```

`gds` and `same` use links written by `compute_similarity.py` — re-run it after ingesting new pages.

Useful Cypher (Neo4j Browser):

```cypher
// listings per department and how the department was decided
MATCH (l:Listing) RETURN l.department, l.deptMethod, count(*) ORDER BY count(*) DESC;
// products sold by several shops, with their EUR prices
MATCH (a:Listing)-[:SAME_PRODUCT]-(b:Listing) RETURN a.title, a.priceEur, collect(DISTINCT [b.priceEur, b.url])[..5];
// black cotton clothing for women under 100 EUR
MATCH (l:Listing {department: 'clothing'})-[:HAS_SPEC]->(:Spec {key: 'color', value: 'black'}),
      (l)-[:HAS_SPEC]->(:Spec {key: 'material', value: 'cotton'}),
      (l)-[:HAS_SPEC]->(:Spec {key: 'gender', value: 'women'})
WHERE l.priceEur < 100 RETURN l.title, l.priceEur, l.url;
```

## How it works

**Extraction** (`extraction.py`, site-agnostic, layers fill only empty fields):
1. schema.org `Product` / `ProductGroup` (+ the variant matching the URL) in JSON-LD or microdata,
   OpenGraph/meta tags, breadcrumbs.
2. Label/value pairs from the main content (tables, `<dl>`, `Label: Value` lines, embedded JSON).
   Headers, footers, menus and cookie banners are skipped; contact details, prices, opening hours
   and marketing copy are filtered out.

**Normalization** (`normalize.py`, vocabulary in `vocab.py`):
- **Department** (22 top-level ones, e.g. clothing, footwear, beauty & personal care, computers,
  cameras & photo, kitchen & dining, automotive…):
  1. multilingual keywords in breadcrumbs / title / URL, including compound words
     (`vinterjakke` → jakke → clothing) and ignoring color words in titles;
  2. otherwise a classifier trained on the confidently keyword-labelled listings (embeddings),
     used when ≥ 50 % confident;
  3. otherwise `other`. `l.deptMethod` / `l.deptConfidence` record how it was decided.
- **Brand**: legal suffixes and aliases removed (`Samsung Electronics Co., Ltd.` → `samsung`);
  missing brands inferred from the title or URL using brands seen elsewhere in the catalog.
- **GTIN** checksum-validated; EAN-like "model numbers" moved to GTIN; SKUs dropped.
- **Specs**: labels in EN/DA/SV/NO/DE/PL mapped to canonical keys; values canonicalized —
  colors (`mørkeblå` → navy), materials ordered by share (`60% bomuld, 40% polyester` → cotton,
  polyester), gender, sizes (`Str. M`, `xxl - int` → m, xxl), condition, and units (`41cm` → 410mm,
  `2,8 liter` → 2800ml, `15,6"` → 15.6inch; `num`/`unit` kept on the Spec node).
- **Price**: any locale format, `kr.` resolved from the shop's TLD, converted to EUR (ECB daily rates).

## Graph model

```
(:Source {domain}) <-[:LISTED_ON]- (:Listing {url, title, price, currency, priceEur, availability,
                                              condition, gtin, department, deptMethod, embedding, …})
   (:Listing)-[:IN_DEPARTMENT]->(:Department {name})
   (:Listing)-[:MADE_BY {w}]->(:Manufacturer {name})
   (:Listing)-[:OF_MODEL {w}]->(:Model {key, name})
   (:Listing)-[:IN_CATEGORY {w}]->(:Category {name})-[:PART_OF]->(:Department)
   (:Listing)-[:HAS_SPEC {w}]->(:Spec {key, value, num, unit})
   (:Listing)-[:SAME_PRODUCT]->(:Listing)       same GTIN, or same manufacturer + model
   (:Listing)-[:SIMILAR {score}]->(:Listing)    weighted Jaccard, within a department
```

`w` is how much a shared attribute counts for similarity (`vocab.SPEC_WEIGHTS`, `REL_WEIGHTS`): a
shared model or brand counts far more than a shared size.

## Extending

- **New language / site labels**: add synonyms to `LABEL_SYNONYMS` / `IGNORED_LABELS` in `vocab.py`.
- **Department mistakes**: add keywords to `DEPARTMENTS` in `vocab.py`, then
  `python ingest.py --from-cache --all` (re-uses the cache, no re-download).
- **Better departments for the hard tail**: an LLM classification step for listings with
  `deptMethod = 'none'` is the natural next upgrade.
- **Ranking**: `W_TEXT`, `W_PRICE` in `similar.py`; `top_k`/`cutoff` in `compute_similarity.py`.

## Files

| File | Purpose |
|---|---|
| `pipeline.sh` | Whole run, asynchronously |
| `crawl.py` / `render.py` | Download / render pages into `cache/` |
| `extraction.py` | HTML → raw product record |
| `vocab.py` | Multilingual vocabularies, departments, similarity weights |
| `normalize.py` | Raw record → canonical record, departments, EUR prices |
| `ingest.py` | Pipeline into Neo4j |
| `compute_similarity.py`, `similar.py` | Similarity links and queries |
| `setup_schema.py`, `common.py`, `start_neo4j.sh`, `docker-compose.yml` | Setup |
