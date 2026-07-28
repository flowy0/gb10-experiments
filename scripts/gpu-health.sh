#!/usr/bin/env bash
# GPU health monitor — watches for NVRM Xid errors and acts
set -euo pipefail

LOG_FILE="/var/log/gpu-health.log"
XID_THRESHOLD=3  # Number of Xid errors before action
XID_WINDOW=3600  # Window in seconds (1 hour)

XID_COUNT=$(journalctl -k --since "1 hour ago" 2>/dev/null | grep -c "NVRM: Xid" || echo 0)

if [ "$XID_COUNT" -ge "$XID_THRESHOLD" ]; then
    echo "$(date): $XID_COUNT Xid errors in last hour — restarting vLLM" | tee -a "$LOG_FILE"
    docker compose restart vllm-qwen36-35b-a3b-nvfp4
fi
