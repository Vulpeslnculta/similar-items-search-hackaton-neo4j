#!/usr/bin/env bash
# Asynchronous end-to-end pipeline: download, render and ingest run concurrently; similarity at the end.
#   ./pipeline.sh links.csv
# Everything is resumable: re-running skips work already done. Progress: cache/*.log
set -uo pipefail
cd "$(dirname "$0")"
CSV=${1:?usage: ./pipeline.sh links.csv}
PY=.venv/bin/python
INGEST_EVERY=${INGEST_EVERY:-300}   # seconds between incremental ingests
mkdir -p cache

$PY -u crawl.py "$CSV" >> cache/crawl.log 2>&1 &
CRAWL=$!

# render domains as soon as their static crawl is finished; one last pass once crawling is done
( while kill -0 $CRAWL 2>/dev/null; do $PY -u render.py "$CSV" >> cache/render.log 2>&1; sleep 60; done
  $PY -u render.py >> cache/render.log 2>&1 ) &
RENDER=$!

# the database fills up while the above keep working
while kill -0 $CRAWL 2>/dev/null || kill -0 $RENDER 2>/dev/null; do
  sleep "$INGEST_EVERY"
  $PY ingest.py --from-cache >> cache/ingest.log 2>&1
done
$PY ingest.py --from-cache >> cache/ingest.log 2>&1
$PY compute_similarity.py >> cache/ingest.log 2>&1
echo "pipeline finished $(date)" >> cache/ingest.log
