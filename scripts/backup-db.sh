#!/usr/bin/env bash
# Back up the research store (claims/evidence/relations) to a GitHub issue.
# The bundle JSON is gzipped + base64 so it fits inside one issue body
# (raw JSON exceeds the ~64KB body limit once the library grows).
set -euo pipefail
cd "$(dirname "$0")/.."

STORE="${STORE:-postgres}"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

uv run science-researcher export-research --store "$STORE" --out "$TMP/bundle.json" >/dev/null
gzip -9c "$TMP/bundle.json" | base64 -w 76 > "$TMP/payload.b64"
SIZE=$(wc -c < "$TMP/payload.b64")
if [ "$SIZE" -gt 60000 ]; then
  echo "payload too large for a single issue body (${SIZE} bytes); split the export first" >&2
  exit 1
fi

gh label create db-backup --color 5319e7 --description "Automated research-store backup snapshot" >/dev/null 2>&1 || true

{
  echo "Automated science-researcher research-store backup (store: \`$STORE\`)."
  echo
  echo "- payload: gzip+base64 of a schema-1 research bundle"
  echo "- restore: \`make restore ISSUE=<this issue number>\`"
  echo
  echo "<!-- science-researcher:db-backup v1 -->"
  echo '```text'
  cat "$TMP/payload.b64"
  echo '```'
} > "$TMP/body.md"

gh issue create \
  --title "db-backup $(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  --body-file "$TMP/body.md" \
  --label db-backup
