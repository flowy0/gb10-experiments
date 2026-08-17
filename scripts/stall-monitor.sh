#!/usr/bin/env bash
# System stall monitor — detects stalls by correlating multiple signals
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

# 1. D-state processes (stuck in kernel I/O)
D_COUNT=$(ps -eo state | grep -c '^D' 2>/dev/null || echo 0)
if [ "$D_COUNT" -gt 10 ] 2>/dev/null; then
    SCORE=$((SCORE + 2))
    SIGNALS="$SIGNALS D-state=$D_COUNT"
fi

# 2. Blocked procs from loadavg
LOADAVG=$(cat /proc/loadavg 2>/dev/null || echo "0.00 0.00 0.00 1/1 1")
BLOCKED=$(echo "$LOADAVG" | awk -F/ '{print $2}' | awk '{print $1}' 2>/dev/null || echo 0)
if [ "$BLOCKED" -gt 5 ] 2>/dev/null; then
    SCORE=$((SCORE + 2))
    SIGNALS="$SIGNALS blocked=$BLOCKED"
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

# 7. Model responsiveness — TWO checks: API server reachable AND engine can actually generate
# (2026-08-11: /v1/models alone missed a 38h engine deadlock — the API server kept answering 200)
# 2026-08-17: parameterized for candidate sessions — defaults to aeon; override for sglang session:
#   MONITOR_PORT=8888 MONITOR_MODEL=qwen3.8-27b-sglang MONITOR_CONTAINER=sglang-qwen38 ./stall-monitor.sh
MONITOR_PORT="${MONITOR_PORT:-8000}"
MONITOR_MODEL="${MONITOR_MODEL:-aeon-qwen36-35b-128k-think}"
MONITOR_CONTAINER="${MONITOR_CONTAINER:-aeon-qwen36-35b}"
if ! curl -sf --max-time 10 "http://127.0.0.1:${MONITOR_PORT}/v1/models" > /dev/null 2>&1; then
    SCORE=$((SCORE + 1))
    SIGNALS="$SIGNALS model_api_down"
elif ! curl -sf --max-time 45 -X POST "http://127.0.0.1:${MONITOR_PORT}/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"${MONITOR_MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":1}" \
        > /dev/null 2>&1; then
    SCORE=$((SCORE + 3))
    SIGNALS="$SIGNALS model_engine_stalled"
fi

# 7. Failed systemd services
FAILED=$(systemctl --failed --no-legend 2>/dev/null | wc -l || echo 0)
if [ "$FAILED" -gt 2 ] 2>/dev/null; then
    SCORE=$((SCORE + 1))
    SIGNALS="$SIGNALS failed_services=$FAILED"
fi

if [ "$SCORE" -ge 5 ]; then
    log "STALL DETECTED (score=$SCORE):$SIGNALS"
    log "Killing llama-swap models + restarting model engine"
    docker ps --filter name=ls- --format '{{.Names}}' | xargs docker rm -f 2>/dev/null || true
    # 2026-08-11: target was stale (vllm-qwen36-35b-a3b-nvfp4 is commented out) — now points at active AEON service
    # 2026-08-17: target follows MONITOR_CONTAINER (defaults to aeon-qwen36-35b)
    docker compose -f /opt/atom/docker-compose.yml restart "${MONITOR_CONTAINER}" 2>/dev/null || true
elif [ "$SCORE" -ge 3 ]; then
    log "WARNING (score=$SCORE):$SIGNALS"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') OK (score=$SCORE)" >> "$LOG_FILE"
fi
