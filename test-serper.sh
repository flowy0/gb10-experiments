#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-/opt/atom/.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  exit 1
fi

# Safely load simple KEY=VALUE lines from .env
set -a
source "$ENV_FILE"
set +a

if [[ -z "${SERPER_API_KEY:-}" ]]; then
  echo "ERROR: SERPER_API_KEY is not set in $ENV_FILE" >&2
  exit 1
fi

QUERY="${2:-NVIDIA DGX Spark GB10 release notes}"

echo "Testing Serper API key from: $ENV_FILE"
echo "Query: $QUERY"
echo

HTTP_CODE="$(
  curl -sS -o /tmp/serper-response.json -w "%{http_code}" \
    -X POST "https://google.serper.dev/search" \
    -H "X-API-KEY: ${SERPER_API_KEY}" \
    -H "Content-Type: application/json" \
    --data "$(jq -nc --arg q "$QUERY" '{q: $q}')"
)"

echo "HTTP status: $HTTP_CODE"
echo

if [[ "$HTTP_CODE" == "200" ]]; then
  echo "SUCCESS: Serper key works."
  echo
  echo "Top results:"
  jq -r '
    .organic[0:5][]? |
    "- " + (.title // "Untitled") + "\n  " + (.link // "No link") + "\n  " + (.snippet // "")
  ' /tmp/serper-response.json
else
  echo "FAILED: Serper returned HTTP $HTTP_CODE"
  echo
  echo "Response body:"
  cat /tmp/serper-response.json
  echo
  exit 1
fi
