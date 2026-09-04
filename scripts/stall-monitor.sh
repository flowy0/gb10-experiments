#!/usr/bin/env bash
# stall-monitor.sh — system + model-engine stall detection.
# 2026-09-04: engine check is now metrics-aware (busy vs stalled). Giant prompts
# (100K+ token prefill) legitimately saturate SGLang for minutes — a probe timeout
# queued behind one is NOT a deadlock, but it used to trigger a restart (killed a
# live engine mid-prefill twice on 2026-09-04: 12:01 and 13:34). Detection now:
#   engine idle           -> generation probe (catches the 2026-08-11 idle deadlock)
#   engine busy + progress-> healthy (probe skipped; never counts as a stall)
#   engine busy, frozen   -> confirmed stall (no completed batch / no token move
#                            across two 30s windows)
# Progress = completed scheduler batch log lines (primary) OR the monotonic token
# counters (secondary): giant cache-replay prefills process tokens without always
# ticking prompt_tokens_total (killed a healthy engine twice on 2026-09-04), but
# every completed batch prints a "Prefill/Decode batch" line.
# Also removed the bogus "blocked" loadavg signal: it read the TOTAL task count
# from /proc/loadavg (running/total, ~1400 on this box) as "blocked" — a permanent
# +2 that silently lowered the restart threshold.
set -euo pipefail

LOG_FILE="/tmp/stall-monitor.log"
LOCK_FILE="/tmp/stall-monitor.lock"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG_FILE"
}

# Prevent concurrent runs
exec 200>"$LOCK_FILE"
flock -n 200 || exit 0

SCORE=0
SIGNALS=""
ENGINE_STALLED=0

MONITOR_PORT="${MONITOR_PORT:-8888}"
MONITOR_MODEL="${MONITOR_MODEL:-radixark-qwen38-27b-nvfp4-dflash2-262k-think}"
MONITOR_CONTAINER="${MONITOR_CONTAINER:-sglang-qwen38}"
API_URL="http://127.0.0.1:${MONITOR_PORT}/v1/models"
METRICS_URL="http://127.0.0.1:${MONITOR_PORT}/metrics"

# --- engine state via SGLang prometheus metrics -------------------------------

# engine_state -> "running queued pending processed_tokens" ("" if metrics absent)
# Fetches ONCE (atomic snapshot). Gauges may read 0 during scheduler-side chunked
# prefill, so busy detection also leans on the monotonic token counters, which are
# summed across ALL series (prompt/generation_tokens_total are split by
# is_streaming="true|false" labels).
engine_state() {
    local body run q pend pt gt
    body=$(curl -sf --max-time 10 "$METRICS_URL" 2>/dev/null) || { echo ""; return; }
    [ -z "$body" ] && { echo ""; return; }
    # literal prefix match via index() — avoids '{' regex-metachar pitfalls
    run=$(printf '%s\n' "$body" | awk -v m='sglang:num_running_reqs{' 'index($0,m)==1 {print $2; exit}')
    q=$(printf '%s\n' "$body" | awk -v m='sglang:num_queue_reqs{' 'index($0,m)==1 {print $2; exit}')
    pend=$(printf '%s\n' "$body" | awk -v m='sglang:pending_prealloc_token_usage{' 'index($0,m)==1 {print $2; exit}')
    pt=$(printf '%s\n' "$body" | awk -v m='sglang:prompt_tokens_total{' 'index($0,m)==1 {s+=$2} END {print s+0}')
    gt=$(printf '%s\n' "$body" | awk -v m='sglang:generation_tokens_total{' 'index($0,m)==1 {s+=$2} END {print s+0}')
    # require the progress counters to exist; else treat metrics as unavailable
    if ! printf '%s\n' "$body" | grep -q '^sglang:prompt_tokens_total{'; then
        echo ""; return
    fi
    awk -v r="${run:-0}" -v u="${q:-0}" -v p="${pend:-0}" -v t="$pt" -v g="$gt" \
        'BEGIN{printf "%s %s %s %s", r, u, p, (t+g)}'
}

field() { echo "$1" | awk -v i="$2" '{print $i}'; }

# busy_p <state> -> exit 0 if any work is outstanding (running/queued/pending)
busy_p() {
    local r u p
    r=$(field "$1" 1); u=$(field "$1" 2); p=$(field "$1" 3)
    awk -v r="${r:-0}" -v u="${u:-0}" -v p="${p:-0}" 'BEGIN{exit !(r>0 || u>0 || p>0)}'
}

# prog_gt <stateA> <stateB> -> exit 0 if processed tokens grew between the samples
prog_gt() {
    local a b
    a=$(field "$1" 4); b=$(field "$2" 4)
    awk -v a="${a:-0}" -v b="${b:-0}" 'BEGIN{exit !(b>a)}'
}

# batch_lines_since <seconds> -> count of scheduler batch completions logged in the
# last N seconds. SGLang prints one "Prefill batch"/"Decode batch" line per completed
# batch — the most direct progress evidence (see header note on cache-replay prefills).
batch_lines_since() {
    docker logs "${MONITOR_CONTAINER}" --since "${1}s" 2>/dev/null \
        | grep -cE '\] (Prefill batch|Decode batch)' || true
}

# engine_made_progress <stateA> <stateB> [lookback_s] -> exit 0 if the engine
# demonstrably worked between the samples: token counters advanced OR a scheduler
# batch completed within the last <lookback_s>s (default 25).
engine_made_progress() {
    local look
    look="${3:-25}"
    prog_gt "$1" "$2" && return 0
    [ "$(batch_lines_since "$look")" -ge 1 ]
}

probe_engine() {   # 0 = generation probe answered (engine alive)
    curl -sf --max-time 45 -X POST "http://127.0.0.1:${MONITOR_PORT}/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"${MONITOR_MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":1}" \
        > /dev/null 2>&1
}

# --- signals ------------------------------------------------------------------

# 1. D-state processes (stuck in uninterruptible kernel I/O). Normally ~0 even
#    under heavy inference load, so >10 indicates a genuinely wedged box.
D_COUNT=$(ps -eo state= | grep -c '^D' 2>/dev/null || echo 0)
if [ "$D_COUNT" -gt 10 ] 2>/dev/null; then
    SCORE=$((SCORE + 2))
    SIGNALS="$SIGNALS D-state=$D_COUNT"
fi

# 3. Kernel alerts (NVRM, Xid, hung tasks)
KERNEL_ALERTS=$(journalctl -k --since "10 minutes ago" 2>/dev/null | grep -ciE 'NVRM|Xid|NV_ERR|blocked for more|hung.task' || echo 0)
if [ "$KERNEL_ALERTS" -gt 0 ] 2>/dev/null; then
    SCORE=$((SCORE + 3))
    SIGNALS="$SIGNALS kernel_alerts=$KERNEL_ALERTS"
fi

# 4. Memory pressure
MEM_PRESSURES=$(journalctl --since "10 minutes ago" 2>/dev/null | grep -c 'Under memory pressure' || echo 0)
if [ "$MEM_PRESSURES" -gt 0 ] 2>/dev/null; then
    SCORE=$((SCORE + 2))
    SIGNALS="$SIGNALS mem_pressure=$MEM_PRESSURES"
fi

# 5. Available memory
MEM_PCT=$(free | awk '/^Mem:/ {printf "%d", $7/$2 * 100}' 2>/dev/null || echo 100)
if [ "$MEM_PCT" -lt 5 ] 2>/dev/null; then
    SCORE=$((SCORE + 2))
    SIGNALS="$SIGNALS mem_free=${MEM_PCT}%"
fi

# 6. SSH responsiveness (can we complete a local ssh-like connect?)
if ! timeout 5 bash -c 'echo test | nc -w 3 127.0.0.1 22 2>/dev/null | grep -q SSH'; then
    SCORE=$((SCORE + 2))
    SIGNALS="$SIGNALS ssh_down"
fi

# 7. Model responsiveness — metrics-aware (see header). API reachable but engine
#    wedged = the 2026-08-11 case (/v1/models answered 200 for 38h); engine busy
#    with a giant prefill = healthy, no matter how long a probe would queue.
if ! curl -sf --max-time 10 "$API_URL" > /dev/null 2>&1; then
    SCORE=$((SCORE + 1))
    SIGNALS="$SIGNALS model_api_down"
else
    STATE1=$(engine_state)
    if [ -n "$STATE1" ] && busy_p "$STATE1"; then
        # Gauges show outstanding work — judge by progress over two 30s windows,
        # NEVER by a probe (it would queue behind the work and time out).
        log "engine busy: running=$(field "$STATE1" 1) queue=$(field "$STATE1" 2) pending=$(field "$STATE1" 3) — watching for progress"
        sleep 30
        STATE2=$(engine_state)
        if [ -n "$STATE2" ] && engine_made_progress "$STATE1" "$STATE2"; then
            log "engine busy, progress in window 1 — healthy"
        else
            sleep 30
            STATE3=$(engine_state)
            if [ -n "$STATE3" ] && engine_made_progress "$STATE2" "$STATE3"; then
                log "engine busy, progress in window 2 — healthy"
            elif [ -n "$STATE3" ] && busy_p "$STATE3"; then
                # still busy and no completed batch / no token movement for 60s
                ENGINE_STALLED=1
                log "engine busy with no progress for 60s — confirmed stall"
            else
                log "engine drained or metrics dropped during watch — healthy"
            fi
        fi
    else
        # Gauges idle — but a chunked prefill can hide here (gauges read 0 while the
        # scheduler chews on a giant prompt). Run the probe; a timeout is ONLY a
        # stall if the engine demonstrably did no work while the probe waited.
        if ! probe_engine; then
            STATEA=$(engine_state)
            if [ -n "$STATE1" ] && [ -n "$STATEA" ] && engine_made_progress "$STATE1" "$STATEA" 60; then
                log "probe timed out but engine made progress (busy with real work) — healthy"
            else
                ENGINE_STALLED=1   # (metrics unavailable: legacy semantics)
            fi
        fi
    fi
    if [ "$ENGINE_STALLED" = 1 ]; then
        SCORE=$((SCORE + 3))
        SIGNALS="$SIGNALS model_engine_stalled"
    fi
fi

# --- verdict ------------------------------------------------------------------

recover() {
    log "Killing llama-swap models + restarting model engine"
    docker ps --filter name=ls- --format '{{.Names}}' | xargs docker rm -f 2>/dev/null || true
    # restart target follows MONITOR_CONTAINER (default sglang-qwen38 since 2026-08-17)
    # SGLang recovery: graceful compose restart works; SIGKILL/manual-kill does not auto-restart (docker semantics)
    docker compose -f /opt/atom/docker-compose.yml restart "${MONITOR_CONTAINER}" 2>/dev/null || true
}

# A CONFIRMED engine stall restarts on its own (score 3 alone would only warn); the
# >=5 branch keeps the multi-signal restart for system-level emergencies.
if [ "$ENGINE_STALLED" = 1 ] || [ "$SCORE" -ge 5 ]; then
    log "STALL DETECTED (score=$SCORE):$SIGNALS"
    recover
elif [ "$SCORE" -ge 3 ]; then
    log "WARNING (score=$SCORE):$SIGNALS"
else
    log "OK (score=$SCORE)"
fi
