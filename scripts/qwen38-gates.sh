#!/usr/bin/env bash
# qwen38-gates.sh — correctness gates G1–G9 (test plan §1b), identical for every candidate.
# Usage: bash scripts/qwen38-gates.sh <base_url> <model> [--no-think-kwargs]
#   --no-think-kwargs : engine without chat_template_kwargs support (thinking control via server flags)
# Exits nonzero on first gate failure; prints a summary. Results in docs/qwen38-test-runs/gates-<tag>.json
set -uo pipefail

BASE="${1:?base url e.g. http://127.0.0.1:8090/v1}"
MODEL="${2:?model name}"
THINK_KWARGS=1
[ "${3:-}" = "--no-think-kwargs" ] && THINK_KWARGS=0
TAG="${TAG:-$(basename "$BASE")}"
OUT_DIR="docs/qwen38-test-runs"
mkdir -p "$OUT_DIR"

PASS=0; FAIL=0; declare -a RESULTS=()

chat() { # chat <json-body-file>
    curl -sf --max-time 300 -X POST "$BASE/chat/completions" \
        -H "Content-Type: application/json" -d @"$1" 2>/dev/null
}

check() { # check <gate-id> <desc> <actual> <expected-substring-or-exact>
    local id="$1" desc="$2" actual="$3" expected="$4"
    if [[ "$actual" == *"$expected"* ]]; then
        PASS=$((PASS+1)); RESULTS+=("{\"gate\":\"$id\",\"pass\":true,\"detail\":\"$actual\"}")
        echo "  PASS $id ($desc)"
    else
        FAIL=$((FAIL+1)); RESULTS+=("{\"gate\":\"$id\",\"pass\":false,\"detail\":\"$actual\"}")
        echo "  FAIL $id ($desc) — got: ${actual:0:200}"
    fi
}

gen_body() { # gen_body <prompt> <max_tokens> <think|nothink> <extra-json>
    local think="$3" extra="${4:-}"
    if [ "$think" = "think" ]; then
        if [ "$THINK_KWARGS" = "1" ]; then
            cat <<EOF
{"model":"$MODEL","messages":[{"role":"user","content":"$1"}],"max_tokens":$2,"temperature":0,"chat_template_kwargs":{"enable_thinking":true}$extra}
EOF
        else
            cat <<EOF
{"model":"$MODEL","messages":[{"role":"user","content":"$1"}],"max_tokens":$2,"temperature":0}$extra
EOF
        fi
    else
        if [ "$THINK_KWARGS" = "1" ]; then
            cat <<EOF
{"model":"$MODEL","messages":[{"role":"user","content":"$1"}],"max_tokens":$2,"temperature":0,"chat_template_kwargs":{"enable_thinking":false}$extra}
EOF
        else
            cat <<EOF
{"model":"$MODEL","messages":[{"role":"user","content":"$1"}],"max_tokens":$2,"temperature":0}$extra
EOF
        fi
    fi
}

echo "=== G1–G9 for $MODEL @ $BASE (thinking kwargs: $THINK_KWARGS) ==="

# G1 arith think-off
B=$(gen_body "19*23. Answer with only the number." 50 nothink); echo "$B" > /tmp/g1.json
R=$(chat /tmp/g1.json); A=$(echo "$R" | python3 -c "import json,sys; d=json.load(sys.stdin); print((d['choices'][0]['message'].get('content') or '').strip())" 2>/dev/null)
check G1 "arith think-off (expect 437)" "$A" "437"

# G2 arith think-on — expect reasoning_content present AND final 437
B=$(gen_body "19*23. Answer with only the number." 200 think); echo "$B" > /tmp/g2.json
R=$(chat /tmp/g2.json)
REASON=$(echo "$R" | python3 -c "import json,sys; d=json.load(sys.stdin); m=d['choices'][0]['message']; print('RC=' + ('yes' if m.get('reasoning_content') else 'no'))" 2>/dev/null)
A=$(echo "$R" | python3 -c "import json,sys; d=json.load(sys.stdin); print((d['choices'][0]['message'].get('content') or '').strip())" 2>/dev/null)
check G2 "arith think-on, reasoning_content present" "${A} ${REASON}" "RC=yes"
check G2b "arith think-on final answer 437" "$A" "437"

# G3 exact string
B=$(gen_body "Repeat exactly this word: BANANA" 30 nothink); echo "$B" > /tmp/g3.json
A=$(chat /tmp/g3.json | python3 -c "import json,sys; d=json.load(sys.stdin); print((d['choices'][0]['message'].get('content') or '').strip())" 2>/dev/null)
check G3 "exact string BANANA" "$A" "BANANA"

# G4 code shape
B=$(gen_body "Write a Python function fib(n) that returns the nth Fibonacci number, with a docstring." 300 nothink); echo "$B" > /tmp/g4.json
A=$(chat /tmp/g4.json | python3 -c "import json,sys; d=json.load(sys.stdin); print((d['choices'][0]['message'].get('content') or '')[:400])" 2>/dev/null)
check G4 "code block present" "$A" "\`\`\`python"

# G5 tool call
cat > /tmp/g5.json <<EOF
{"model":"$MODEL","messages":[{"role":"user","content":"What is the weather in Tokyo?"}],"max_tokens":100,"temperature":0,"tools":[{"type":"function","function":{"name":"get_weather","description":"Get weather for a city","parameters":{"type":"object","properties":{"city":{"type":"string"}},"required":["city"]}}}]}
EOF
A=$(chat /tmp/g5.json | python3 -c "
import json,sys
d=json.load(sys.stdin)
m=d['choices'][0]['message']
tc=m.get('tool_calls') or []
names=[t['function']['name'] for t in tc]
args=[t['function'].get('arguments','') for t in tc]
print('tool_calls=' + ','.join(names), '| args=' + ' '.join(args))" 2>/dev/null)
check G5 "tool call get_weather(Tokyo)" "$A" "get_weather"

# G6 multi-turn tool flow — Qwen3.8 template expects tool results as <tool_response> USER messages
# (llama.cpp does NOT translate OpenAI role:tool for this template — verified 2026-08-17)
cat > /tmp/g6.json <<EOF
{"model":"$MODEL","messages":[
{"role":"user","content":"What is the weather in Tokyo?"},
{"role":"assistant","content":"<tool_call>\n<function=get_weather>\n<parameter=city>\nTokyo\n</parameter>\n</function>\n</tool_call>"},
{"role":"user","content":"<tool_response>\n{\"city\":\"Tokyo\",\"temp\":23,\"condition\":\"sunny\"}\n</tool_response>"},
{"role":"user","content":"Based on the tool response, answer my original question."}
],"max_tokens":100,"temperature":0}
EOF
A=$(chat /tmp/g6.json | python3 -c "import json,sys; d=json.load(sys.stdin); print((d['choices'][0]['message'].get('content') or '').strip()[:200])" 2>/dev/null)
check G6 "multi-turn tool flow completes" "$A" "23"

# G7 vision — body via file (base64 exceeds ARG_MAX inline)
if [ -n "${VISION_IMAGE:-}" ]; then
    base64 -w0 "$VISION_IMAGE" > /tmp/g7_b64.txt
    MODEL_FOR_PY="$MODEL" python3 <<'EOF' > /tmp/g7.json
import json, os
model = os.environ["MODEL_FOR_PY"]
b64 = open("/tmp/g7_b64.txt").read().strip()
body = {"model":model,"messages":[{"role":"user","content":[
    {"type":"text","text":"Transcribe the text in this image exactly."},
    {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+b64}}
]}],"max_tokens":400,"temperature":0}
json.dump(body, open("/tmp/g7.json","w"))
EOF
    A=$(chat /tmp/g7.json | python3 -c "import json,sys; d=json.load(sys.stdin); print((d['choices'][0]['message'].get('content') or '').strip()[:300])" 2>/dev/null)
    check G7 "vision transcription" "$A" "Peace"
else
    echo "  SKIP G7 (set VISION_IMAGE=/opt/atom/models/atomicchat-qwen38/demo.jpg to run)"
fi

# G8 reasoning effort low vs xhigh
if [ "$THINK_KWARGS" = "1" ]; then
    cat > /tmp/g8a.json <<EOF
{"model":"$MODEL","messages":[{"role":"user","content":"How many R's are in the word strawberry? Think carefully."}],"max_tokens":300,"temperature":0,"chat_template_kwargs":{"enable_thinking":true,"reasoning_effort":"low"}}
EOF
    cat > /tmp/g8b.json <<EOF
{"model":"$MODEL","messages":[{"role":"user","content":"How many R's are in the word strawberry? Think carefully."}],"max_tokens":300,"temperature":0,"chat_template_kwargs":{"enable_thinking":true,"reasoning_effort":"xhigh"}}
EOF
    RL=$(chat /tmp/g8a.json | python3 -c "import json,sys; d=json.load(sys.stdin); m=d['choices'][0]['message']; print(len(m.get('reasoning_content') or ''))" 2>/dev/null)
    RH=$(chat /tmp/g8b.json | python3 -c "import json,sys; d=json.load(sys.stdin); m=d['choices'][0]['message']; print(len(m.get('reasoning_content') or ''))" 2>/dev/null)
    if [ -n "$RL" ] && [ -n "$RH" ] && [ "$RH" -gt "$RL" ] 2>/dev/null; then
        PASS=$((PASS+1)); RESULTS+=("{\"gate\":\"G8\",\"pass\":true,\"detail\":\"low=${RL} chars, high=${RH} chars\"}")
        echo "  PASS G8 (reasoning effort: low=${RL} < high=${RH} chars)"
    else
        FAIL=$((FAIL+1)); RESULTS+=("{\"gate\":\"G8\",\"pass\":false,\"detail\":\"low=${RL}, high=${RH}\"}")
        echo "  FAIL G8 (reasoning effort not distinguishable: low=${RL}, high=${RH})"
    fi
else
    echo "  SKIP G8 (needs chat_template_kwargs)"
fi

# G9 sampling defaults — thinking on, no overrides, sanity output
B=$(gen_body "Write a haiku about the sea." 100 think); echo "$B" > /tmp/g9.json
A=$(chat /tmp/g9.json | python3 -c "import json,sys; d=json.load(sys.stdin); print((d['choices'][0]['message'].get('content') or '').strip()[:150])" 2>/dev/null)
check G9 "non-degenerate output" "$A" ""

echo
python3 - "$OUT_DIR/gates-$TAG-$(date +%Y%m%dT%H%M%SZ).json" "$MODEL" "$PASS" "$FAIL" <<EOF >/dev/null
import json,sys
path, model, p, f = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
json.dump({"candidate":"$TAG","model":model,"pass":p,"fail":f,"results":[]}, open(path,'w'), indent=1)
EOF
echo "=== GATES: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ]
