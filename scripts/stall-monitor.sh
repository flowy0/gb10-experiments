#!/usr/bin/env bash
# System stall monitor — checks vLLM responsiveness and acts
set -euo pipefail

LOG_FILE="/var/log/system-stall-monitor.log"
VLLM_URL="http://127.0.0.1:8000/v1/models"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"

# Consecutive failures threshold
MAX_FAILURES=3
FAILURE_COUNT=0

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"
}

check_vllm() {
    curl -sf --max-time 10 "$VLLM_URL" > /dev/null 2>&1
}

check_ssh_stall() {
    # Check if journald is rotating (sign of memory pressure)
    journalctl --since "5 minutes ago" 2>/dev/null | grep -q "Under memory pressure, flushing caches"
}

for i in $(seq 1 "$MAX_FAILURES"); do
    if check_vllm; then
        FAILURE_COUNT=0
        exit 0
    fi
    FAILURE_COUNT=$((FAILURE_COUNT + 1))
    log "WARN: vLLM unresponsive (attempt $i/$MAX_FAILURES)"
    
    if check_ssh_stall; then
        log "CRITICAL: System memory pressure detected — killing llama-swap models"
        docker ps --filter name=ls- --format '{{.Names}}' | xargs docker rm -f 2>/dev/null || true
        docker compose restart vllm-qwen36-35b-a3b-nvfp4 2>/dev/null || true
        exit 2
    fi
    
    sleep 30
done

log "CRITICAL: vLLM down for ${MAX_FAILURES} checks — restarting" 
docker compose restart vllm-qwen36-35b-a3b-nvfp4 2>/dev/null || true
exit 1
