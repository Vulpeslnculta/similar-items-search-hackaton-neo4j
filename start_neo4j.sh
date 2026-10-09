#!/usr/bin/env bash
# Starts Neo4j in Docker using the password from password.txt.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f password.txt ]; then
  echo "Missing password.txt - put your Neo4j password in it (see README.md)" >&2
  exit 1
fi

lines=$(tr -d '\r' < password.txt | grep -v '^[[:space:]]*$' || true)
count=$(printf '%s\n' "$lines" | grep -c . || true)
if [ "$count" -ge 2 ]; then
  user=$(printf '%s\n' "$lines" | sed -n 1p)
  pass=$(printf '%s\n' "$lines" | sed -n 2p)
else
  user=neo4j
  pass=$(printf '%s\n' "$lines" | sed -n 1p)
fi

if [ "$user" != "neo4j" ]; then
  echo "The Docker image only creates the 'neo4j' user; set the username line to neo4j (or use one line)." >&2
  exit 1
fi
if [ ${#pass} -lt 8 ]; then
  echo "Neo4j requires a password of at least 8 characters." >&2
  exit 1
fi

NEO4J_PASSWORD="$pass" docker compose up -d
echo "Waiting for Neo4j on http://localhost:7474 ..."
for _ in $(seq 1 60); do
  if curl -fs http://localhost:7474 >/dev/null 2>&1; then echo "Neo4j is up."; exit 0; fi
  sleep 2
done
echo "Neo4j didn't respond within 2 minutes - check: docker logs neo4j-listings" >&2
exit 1
