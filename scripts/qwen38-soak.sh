#!/usr/bin/env bash
# qwen38-soak.sh — 45-min mixed-traffic soak for the winner (test plan §6a).
# Usage: bash scripts/qwen38-soak.sh [minutes]
set -uo pipefail

DURATION="${1:-45}"
BASE="http://127.0.0.1:8888/v1"
MODEL="radixark-qwen38-27b-nvfp4-dspark-262k-think"
LOG="/tmp/soak-qwen38.log"
declare -i OK=0 FAIL=0
T0=$(date +%s)
END=$((T0 + DURATION * 60))

echo "soak start $(date -Is) — ${DURATION}min, model $MODEL" > "$LOG"

req() { # req <label> <max_tokens> <thinking> <payload-json-file or prompt>
    local label="$1" mt="$2" think="$3" payload="$4"
    local t0 elapse think_py
    [ "$think" = "true" ] && think_py=True || think_py=False
    t0=$(date +%s%N)
    local body
    if [ -f "$payload" ]; then
        body=$(cat "$payload")
    else
        body=$(python3 -c "
import json,sys
print(json.dumps({'model':'$MODEL','messages':[{'role':'user','content':'''$payload'''}],'max_tokens':$mt,'temperature':0,'chat_template_kwargs':{'enable_thinking':$think_py}}))")
    fi
    local code
    code=$(curl -sf --max-time 300 -o /dev/null -w "%{http_code}" -X POST "$BASE/chat/completions" \
        -H "Content-Type: application/json" -d "$body" 2>/dev/null)
    elapse=$(( ($(date +%s%N) - t0) / 1000000 ))
    if [ "$code" = "200" ]; then
        OK=$((OK+1))
        echo "$(date +%H:%M:%S) OK   $label ${elapse}ms" >> "$LOG"
    else
        FAIL=$((FAIL+1))
        echo "$(date +%H:%M:%S) FAIL $label http=$code ${elapse}ms" >> "$LOG"
    fi
}

mkdir -p /tmp/soak
cat > /tmp/soak/tool.json <<EOF
{"model":"$MODEL","messages":[{"role":"user","content":"What is the weather in Tokyo?"}],"max_tokens":60,"temperature":0,"tools":[{"type":"function","function":{"name":"get_weather","description":"Get weather for a city","parameters":{"type":"object","properties":{"city":{"type":"string"}},"required":["city"]}}}]}
EOF
B64=$(base64 -w0 /opt/atom/models/atomicchat-qwen38/demo.jpg)
base64 -w0 /opt/atom/models/atomicchat-qwen38/demo.jpg > /tmp/soak/b64.txt
MODEL_FOR_PY="$MODEL" python3 <<'PY' > /tmp/soak/vision.json
import json, os
model = os.environ["MODEL_FOR_PY"]
b64 = open("/tmp/soak/b64.txt").read().strip()
json.dump({"model":model,"messages":[{"role":"user","content":[
  {"type":"text","text":"Describe this image in one sentence."},
  {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+b64}}]}],
  "max_tokens":80,"temperature":0}, open("/tmp/soak/vision.json","w"))
PY

CYCLE=0
while [ "$(date +%s)" -lt "$END" ]; do
    CYCLE=$((CYCLE+1))
    req "chat-short-$CYCLE"       30 false "What is the capital of France?"
    req "chat-long-$CYCLE"       400 false "Write a detailed explanation of how paging works in operating systems."
    req "think-$CYCLE"           200 true  "Explain the difference between MTP and DSpark in one paragraph."
    req "tool-$CYCLE"            60  false /tmp/soak/tool.json
    req "vision-$CYCLE"          80  false /tmp/soak/vision.json
    if [ $((CYCLE % 3)) -eq 0 ]; then
        # concurrent pair
        req "conc-a-$CYCLE" 150 false "Write a short poem about the sea." &
        req "conc-b-$CYCLE" 150 false "Write a short poem about mountains." &
        wait
    fi
    RSS=$(docker stats sglang-qwen38 --no-stream --format '{{.MemUsage}}' 2>/dev/null)
    echo "$(date +%H:%M:%S) rss $RSS" >> "$LOG"
    echo "cycle $CYCLE — OK=$OK FAIL=$FAIL (rss: $RSS)"
    sleep 20
done

echo "soak end $(date -Is) — OK=$OK FAIL=$FAIL" >> "$LOG"
echo "SOAK DONE: OK=$OK FAIL=$FAIL — full log: $LOG"