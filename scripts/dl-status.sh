#!/usr/bin/env bash
# Qwen3.8 Stage-0 download status — shows everything at once.
# Usage: bash scripts/dl-status.sh   (or run repeatedly to watch progress)

echo "=== active download processes ==="
PROCS=$(ps aux | grep -E "hf download|docker pull" | grep -v grep)
if [ -z "$PROCS" ]; then
    echo "  (none — all downloads finished or failed)"
else
    echo "$PROCS" | awk '{print "  PID " $2 ": " $12 " " $13 " " $14}'
fi

echo
echo "=== HF model files (target sizes) ==="
declare -A EXPECT=(
    ["atomicchat-qwen38/Qwen3.8-27B-AD-Q5_K_M-Q4_K_M.gguf"]="18.55GB"
    ["atomicchat-qwen38/mmproj-Qwen3.8-27B-F16.gguf"]="0.93GB"
    ["atomicchat-qwen38/demo.jpg"]="0.33MB"
    ["hf-cache/hub/models--RadixArk--Qwen3.8-27B-NVFP4/blobs"]="18.2GB"
    ["hf-cache/hub/models--Qwen--Qwen3.8-27B-FP8/blobs"]="28.5GB"
    ["hf-cache/hub/models--Doopeworld--Qwen3.8-27B-DSpark-vLLM/blobs"]="2.6GB"
)
for path in "${!EXPECT[@]}"; do
    full="/opt/atom/models/$path"
    if [ -e "$full" ]; then
        size=$(du -sh "$full" 2>/dev/null | cut -f1)
        printf "  %-75s %8s  (target %s)\n" "$path" "$size" "${EXPECT[$path]}"
    else
        printf "  %-75s %8s  (target %s)\n" "$path" "MISSING" "${EXPECT[$path]}"
    fi
done

echo
echo "=== docker images ==="
docker images --format '{{.Repository}}:{{.Tag}}  {{.Size}}' 2>/dev/null | grep -E "sglang:qwen38|vllm-openai:v0.27.1|llama.cpp:server-cuda13 " || echo "  (none matching yet)"

echo
echo "=== per-repo file count (HF cache) ==="
for repo in models--RadixArk--Qwen3.8-27B-NVFP4 models--Qwen--Qwen3.8-27B-FP8 models--Doopeworld--Qwen3.8-27B-DSpark-vLLM; do
    n=$(ls /opt/atom/models/hf-cache/hub/$repo/snapshots/*/ 2>/dev/null | wc -l)
    echo "  $repo: $n files in snapshot"
done
