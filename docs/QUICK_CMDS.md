# Quick Commands

## Model Downloads

### HuggingFace (via `hf`)
```bash
# Download entire model repo
hf download <org/model-name> --local-dir /opt/atom/models/<dir>

# Download a single file
hf download <org/model-name> <filename> --local-dir /opt/atom/models/<dir>

# Examples
hf download unsloth/Qwen3.6-27B-MTP-GGUF Qwen3.6-27B-UD-Q2_K_XL.gguf \
  --local-dir /opt/atom/models/unsloth-qwen3.6-27b-mtp-gguf

hf download yuxinlu1/gemma-4-12B-agentic-fable5-composer2.5-v2-3.5x-tau2-GGUF \
  --local-dir /opt/atom/models/yuxinlu1-gemma4-12b-agentic-v2
```

### Monitor download progress
```bash
# Check size
du -sh /opt/atom/models/<dir>/

# Check if still running
ps aux | grep "hf download" | grep -v grep

# View download log
tail -f /opt/atom/models/<dir>/download.log
```

### Clean up partial / failed downloads
```bash
# Kill stale process
kill <PID>

# Remove partial cache
rm -rf /opt/atom/models/<dir>/.cache
rm -f /opt/atom/models/<dir>/*.gguf /opt/atom/models/<dir>/*.safetensors
```

## Model Config

### Edit llama-swap config
```bash
nano /opt/atom/llama-swap/config.yaml
```

### Validate YAML
```bash
python3 -c "import yaml; yaml.safe_load(open('/opt/atom/llama-swap/config.yaml')); print('✅')"
```

### Validate Docker Compose
```bash
docker compose -f /opt/atom/docker-compose.yml config > /dev/null && echo "✅"
```

## Container Management

### Restart services
```bash
# Restart llama-swap (picks up config changes)
docker compose -f /opt/atom/docker-compose.yml restart llama-swap

# Restart vLLM with new config
docker compose -f /opt/atom/docker-compose.yml up -d vllm-gemma4 --force-recreate

# Restart everything
docker compose -f /opt/atom/docker-compose.yml restart
```

### Force-recreate a specific container
```bash
docker compose -f /opt/atom/docker-compose.yml up -d <service> --force-recreate
```

### Check container status
```bash
# All containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Filter by service
docker ps --filter name=vllm --format "{{.Names}} {{.Status}}"
docker ps --filter name=ls- --format "{{.Names}} {{.Status}}"
```

### View logs
```bash
# Follow live
docker logs -f <container-name>

# Recent tail
docker logs <container-name> 2>&1 | tail -20

# Filter by keyword
docker logs <container-name> 2>&1 | grep -E "error|timing|model"
```

### Kill a running model container (llama-swap managed)
```bash
docker rm -f ls-<model-name>
```

## Testing

### Quick test (loads model on first request)
```bash
curl -s --max-time 180 -X POST http://127.0.0.1:8088/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"<model-id>","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
```

```bash 
  curl -s --max-time 180 -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"unsloth-gemma4-26b-a4b-fp8-256k-think-mtp3","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
```


```bash 
  curl -s --max-time 180 -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"unsloth-gemma4-26b-a4b-fp8-128k-think-mtp1","messages":[{"role":"user","content":"hi"}],"max_tokens":10}' | jq '{content: .choices[0].message.content, reasoning: (.choices[0].message.reasoning_content // .choices[0].message.reasoning), tokens: .usage.completion_tokens}'
```



### List available models
```bash
# llama-swap — just model IDs
curl -s http://127.0.0.1:8088/v1/models | jq -r '.data[].id'

# vLLM — just model IDs
curl -s http://127.0.0.1:8000/v1/models | jq -r '.data[].id'
```

### Benchmark decode speed
```bash
curl -s -X POST http://127.0.0.1:8088/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"<model-id>","messages":[{"role":"user","content":"hi"}],"max_tokens":100}' \
  | jq -r '"\(.usage.completion_tokens) tok in \(.timings.predicted_ms/1000 | floor)s = \(.usage.completion_tokens / (.timings.predicted_ms/1000) | floor) tok/s"'
```

### Test tool calling
```bash
curl -s -X POST http://127.0.0.1:8088/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"<model-id>","messages":[{"role":"user","content":"What is the weather in Paris?"}],"tools":[{"type":"function","function":{"name":"get_weather","description":"Get weather","parameters":{"type":"object","properties":{"city":{"type":"string"}},"required":["city"]}}}],"max_tokens":100}' \
  | jq '{tool_calls: .choices[0].message.tool_calls, finish: .choices[0].finish_reason}'
```

## Git

```bash
# Check what changed
git diff --stat

# Commit
git add -A && git commit -m "message" && git push

# Roll back a file
git checkout HEAD -- <file>
```
