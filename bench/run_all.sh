#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
uv sync
if [[ ! -f prompts/generated/answer_keys.json ]]; then
  ./run_generate_prompts.sh
fi

echo "Current AI containers:"
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' | grep -E 'NAMES|llama|qwen|gemma|granite|devstral|vllm|litellm|librechat|mongo' || true

echo
read -r -p "Run benchmark now? This can take a long time. [y/N] " ans
case "$ans" in
  y|Y|yes|YES) ;;
  *) echo "cancelled"; exit 0 ;;
esac
uv run python run_bench.py "$@"
