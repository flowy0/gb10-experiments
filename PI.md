# /opt/atom — GB10 Local AI Stack

## Overview
Multi-model LLM serving stack on NVIDIA GB10 (122 GB unified VRAM) using llama-swap + llama.cpp.

## Architecture
```
[pi/Mac] → [llama-swap (port 8088)] → [llama.cpp containers]
  [LibreChat (port 3080)]
  [Open WebUI (port 3000)]
```

## Active Models (93 GB total, 29 GB free)

| Role | Model | Group |
|---|---|---|
| pi coding | `unsloth-qwen36-35b-a3b-mtp-iq4-256k` | mtp-test |
| Hermes main | `unsloth-gemma4-26b-a4b-qat-256k-think` | hermes |
| Hermes aux | `unsloth-gemma4-e4b-qat-q4-256k` | summary |

## Key Commands

### Config
```bash
python3 -c "import yaml; yaml.safe_load(open('llama-swap/config.yaml'))"  # Validate
docker compose restart llama-swap  # Reload config
```

### Testing
```bash
curl -X POST http://localhost:8088/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"<model-id>","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'
```

### Managing Models
```bash
docker ps | grep ls-  # List loaded models
docker rm -f ls-<name>  # Force-unload a model
git checkout HEAD -- llama-swap/config.yaml  # Restore corrupted config
```

## Hardware
- NVIDIA GB10 (Blackwell)
- 122 GB unified VRAM
- 20 CPU threads
- 3.7 TB NVMe storage
