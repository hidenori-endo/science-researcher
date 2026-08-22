#!/usr/bin/env bash
# Restore the research store from a db-backup GitHub issue.
# Usage: scripts/restore-db.sh <issue-number>
# Env: STORE=sqlite|postgres (default sqlite), DB=<sqlite path> (default restored.db)
set -euo pipefail
cd "$(dirname "$0")/.."

ISSUE="${1:?usage: restore-db.sh <issue-number>}"
STORE="${STORE:-sqlite}"
DB="${DB:-restored.db}"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

gh issue view "$ISSUE" --json body -q .body \
  | awk '/science-researcher:db-backup v1/{flag=1; next} /^```$/{flag=0} flag' \
  | tr -d '\n' > "$TMP/payload.b64"
base64 -d "$TMP/payload.b64" | gunzip > "$TMP/bundle.json"

if [ "$STORE" = "sqlite" ]; then
  rm -f "$DB"
  uv run science-researcher init --db "$DB" >/dev/null
  uv run science-researcher import-research --db "$DB" "$TMP/bundle.json" >/dev/null
  echo "restored into sqlite:$DB"
else
  uv run science-researcher import-research --store postgres "$TMP/bundle.json" >/dev/null
  echo "restored into postgres"
fi

uv run python - "$TMP/bundle.json" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
print(f"bundle contents: {len(d['claims'])} claims, {len(d['evidence'])} evidence, {len(d['relations'])} relations")
EOF
