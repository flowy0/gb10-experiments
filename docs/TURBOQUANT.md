# TurboQuant — KV Cache Compression for llama.cpp

TurboQuant compresses the KV cache beyond standard Q8_0, reducing memory by ~25-50% with minimal accuracy loss. Works at runtime — no special GGUF files needed.

## Build

```bash
# Clone the turboquant fork
cd /opt/atom
git clone --branch feature/turboquant-kv-cache \
  https://github.com/TheTom/llama-cpp-turboquant.git llama-cpp-turboquant

# Build Docker image (takes 30-60 min)
cd llama-cpp-turboquant
docker build -t llama-cpp-turboquant:latest .
```

## Cache Types

| Flag | K bits | V bits | Compression vs Q8 |
|---|---|---|---|
| `turbo4` | 8-bit (WHT) | 4-bit (PolarQuant) | ~25% |
| `turbo3` | 8-bit (WHT) | 3-bit (PolarQuant) | ~31% |
| `turbo2` | 8-bit (WHT) | 2-bit (PolarQuant) | ~38% |

Recommended: `--cache-type-k turbo4 --cache-type-v turbo4` for best quality/size tradeoff.

## Usage

Replace the standard image SHA in `llama-swap/config.yaml` and change cache types:

```yaml
# Before (standard llama.cpp)
ghcr.io/ggml-org/llama.cpp:server-cuda13@sha256:bb435df...
--cache-type-k q8_0 --cache-type-v q8_0

# After (turboquant)
llama-cpp-turboquant:latest
--cache-type-k turbo4 --cache-type-v turbo4
```

## Memory Savings

| Model | Context | Std Q8 | TQ turbo4 | Saved |
|---|---|---|---|---|
| 26B QAT | 256k | 30 GB | 22 GB | **+8 GB** |
| 26B QAT | 128k | 15 GB | 11 GB | +4 GB |
| E4B QAT | 256k | 10 GB | 8 GB | +3 GB |
| Qwen 35B | 256k | 10 GB | 8 GB | +2 GB |

## Known Issues

- Prompt eval speed may be slower with turboquant (observed ~1 tok/s vs normal)
- Decode speed unaffected (~70 tok/s for 4B model)
- Tested on Qwen3.5 4B, other models may vary
- Build based on llama.cpp fork b0-unknown (not official release)
