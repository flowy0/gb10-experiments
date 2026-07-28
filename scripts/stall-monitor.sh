#!/usr/bin/env bash
# System stall monitor — detects system-wide stalls by correlating multiple signals
set -euo pipefail

LOG_FILE="/var/log/stall-monitor.log"
LOCK_FILE="/tmp/stall-monitor.lock"

# Thresholds
D_STATE_THRESHOLD=10   # Number of D-state processes before warning
BLOCKED_THRESHOLD=5    # Number of blocked procs before warning

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"
}

# Prevent concurrent runs
exec 200>"$LOCK_FILE"
flock -n 200 || exit 0

SCORE=0
SIGNALS=""

# 1. Check for D-state processes (stuck in kernel)
D_COUNT=$(ps -eo state | grep -c '^D' || echo 0)
if [ "$D_COUNT" -gt "$D_STATE_THRESHOLD" ]; then
    SCORE=$((SCORE + 2))
    SIGNALS="$SIGNALS D-state=$D_COUNT"
fi

# 2. Check for blocked procs
BLOCKED=$(cat /proc/loadavg | awk '{print $4}' | cut -d/ -f2 2>/dev/null || echo 0)
if [ "$BLOCKED" -gt "$BLOCKED_THRESHOLD" ]; then
    SCORE=$((SCORE + 2))
    SIGNALS="$SIGNALS blocked=$BLOCKED"
fi

# 3. Check kernel logs for NVRM/Xid errors (last 5 min)
KERNEL_ALERTS=$(journalctl -k --since "5 minutes ago" 2>/dev/null | grep -ciE 'NVRM|Xid|NV_ERR|blocked for more|hung.task' || echo 0)
if [ "$KERNEL_ALERTS" -gt 0 ]; then
    SCORE=$((SCORE + 3))
    SIGNALS="$SIGNALS kernel_alerts=$KERNEL_ALERTS"
fi

# 4. Check for memory pressure across multiple services
MEM_PRESSURES=$(journalctl --since "5 minutes ago" 2>/dev/null | grep -c 'Under memory pressure' || echo 0)
if [ "$MEM_PRESSURES" -gt 0 ]; then
    SCORE=$((SCORE + 1))
    SIGNALS="$SIGNALS mem_pressure=$MEM_PRESSURES"
fi

# 5. Check available memory
MEM_PCT=$(free | awk '/^Mem:/ {printf "%.0f", $7/$2 * 100}' 2>/dev/null || echo 100)
if [ "$MEM_PCT" -lt 5 ]; then
    SCORE=$((SCORE + 2))
    SIGNALS="$SIGNALS mem_free=${MEM_PCT}%"
fi

# 6. Check vLLM responsiveness
if ! curl -sf --max-time 10 http://127.0.0.1:8000/v1/models > /dev/null 2>&1; then
    SCORE=$((SCORE + 1))
    SIGNALS="$SIGNALS vllm_down"
fi

# 7. Check for failing services
FAILED_SERVICES=$(systemctl --failed --no-legend 2>/dev/null | wc -l || echo 0)
if [ "$FAILED_SERVICES" -gt 0 ]; then
    SCORE=$((SCORE + 1))
    SIGNALS="$SIGNALS failed_services=$FAILED_SERVICES"
fi

# Score interpretation
if [ "$SCORE" -ge 5 ]; then
    log "STALL DETECTED (score=$SCORE):$SIGNALS"
    log "Action: killing llama-swap models and restarting vLLM"
    docker ps --filter name=ls- --format '{{.Names}}' | xargs docker rm -f 2>/dev/null || true
    docker compose restart vllm-qwen36-35b-a3b-nvfp4 2>/dev/null || true
elif [ "$SCORE" -ge 3 ]; then
    log "WARNING (score=$SCORE):$SIGNALS — monitoring"
else
    log "OK (score=$SCORE)"
fi

exit 0
