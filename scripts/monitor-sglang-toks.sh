#!/usr/bin/env bash
# monitor-sglang-toks.sh — sample SGLang decode throughput from the container log.
# Writes a CSV to /tmp/sglang-toks.csv: epoch,time,running_req,gen_tok_s,accept_rate
# Usage: nohup bash scripts/monitor-sglang-toks.sh 15 >/dev/null 2>&1 &
set -uo pipefail

INTERVAL="${1:-15}"
CSV=/tmp/sglang-toks.csv
[ -f "$CSV" ] || echo "epoch,time,running_req,gen_tok_s,accept_rate" > "$CSV"

while true; do
  # last decode-batch line within the interval
  LINE=$(docker logs sglang-qwen38 --since "${INTERVAL}s" 2>&1 | grep "Decode batch" | tail -1)
  if [ -n "$LINE" ]; then
    GEN=$(echo "$LINE" | grep -oP 'gen throughput \(token/s\): \K[0-9.]+' | head -1)
    RUN=$(echo "$LINE" | grep -oP '#running-req: \K[0-9]+' | head -1)
    ACC=$(echo "$LINE" | grep -oP 'accept rate: \K[0-9.]+' | head -1)
    [ -z "$GEN" ] && GEN=0
    [ -z "$RUN" ] && RUN=0
    [ -z "$ACC" ] && ACC=0
    echo "$(date +%s),$(date +%H:%M:%S),${RUN},${GEN},${ACC}" >> "$CSV"
  else
    echo "$(date +%s),$(date +%H:%M:%S),0,0,0" >> "$CSV"
  fi
  sleep "$INTERVAL"
done
