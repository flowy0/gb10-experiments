# vLLM on DGX Spark (GB10) — Setup & Debugging

## Quick Reference

| Item | Value |
|---|---|
| **Image** | `vllm-node-tf5:latest` (custom build) |
| **FP8 Model** | `RedHatAI/gemma-4-26B-A4B-it-FP8-Dynamic` (27 GB) |
| **Assistant** | `google/gemma-4-26B-A4B-it-assistant` (872 MB) |
| **Build source** | `build/spark-vllm-docker/` (cloned from eugr/spark-vllm-docker) |
| **vLLM version** | `0.22.1rc1.dev403+g7852e50e4.d20260611` |

## Build

```bash
cd build/spark-vllm-docker
./build-and-copy.sh -t vllm-node-tf5 --tf5
```

Requires: Docker BuildKit, ~100 GB disk, ~1-2 hours. Builds for Blackwell SM121 (`TORCH_CUDA_ARCH_LIST="12.1a"`) with Transformers v5.

## Usage

### Docker Compose

```bash
docker compose -f docker-compose.yml up -d vllm-gemma4
```

Serves on port 8000. Configured for 256k context, MTP γ=4, 0.65 GPU utilization.

### Manual

```bash
docker run --gpus all --network host --ipc=host --shm-size=64gb \
  --entrypoint vllm \
  -v /opt/atom/models/gemma-4-26b-a4b-it-fp8-dynamic:/model:ro \
  -v /opt/atom/models/gemma-4-26b-a4b-it-assistant:/assistant:ro \
  vllm-node-tf5:latest serve /model \
  --speculative-config '{"method":"mtp","model":"/assistant","num_speculative_tokens":4}' \
  --port 8060 --max-model-len 262144 --gpu-memory-utilization 0.65 \
  --max-num-seqs 4 --kv-cache-dtype fp8 --load-format safetensors
```

### Benchmark

```bash
curl -X POST http://localhost:8060/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"/model","messages":[{"role":"user","content":"Write a paragraph"}],"max_tokens":200}'
```

## Performance (DGX Spark GB10)

| Config | tok/s | Notes |
|---|---|---|
| vLLM FP8 + MTP γ=4 @ 256k | **55** | Tested, verified |
| vLLM FP8 + MTP γ=4 @ 32k | **55-62** | Tested, verified |
| vLLM NVFP4 (no MTP) | **26** | Marlin decompression bottleneck |
| vLLM FP8 no MTP | **26** | Baseline |
| llama-swap QAT + MTP @ 256k | **108** | 2× faster |
| llama-swap QAT no MTP @ 256k | **82** | 1.5× faster |

## Memory

With `--gpu-memory-utilization 0.65`:
- Reserved: 79 GB
- Model + assistant: ~30 GB
- KV cache @ 256k: ~30 GB
- Remaining: **43 GB** (can run E4B QAT 17 GB alongside)

## Multi-Session

vLLM uses PagedAttention — each session gets isolated KV cache. Tested with 4 concurrent sessions:
- 575-657 total tokens across 4 sessions
- No context compaction/eviction

## Known Issues

### MTP Config

The working speculative config uses `"method":"mtp"`. Some articles use `"method":"gemma4_mtp"` — both work on this build.

### CUDA Graph Compilation

First load is slow (~3 min for 27 GB model + 256k cache + CUDA graph compilation). Subsequent loads are faster.

### Memory Cleanup

After stopping vLLM, zombie `VLLM::EngineCore` processes may hold GPU memory. Clean with:

```bash
docker rm -f $(docker ps -aq --filter name=gemma4-) $(docker ps -aq --filter name=vllm-)
```

## Investigation History

### vLLM Stock Images — CUTLASS Crash

All stock `vllm/vllm-openai` images crash on Blackwell (SM121) with:
```
RuntimeError: cutlass_gemm_caller ... Error Internal
```
Root cause: CUTLASS FP8 kernels lack SM121 support in stock builds.

### NVIDIA NGC Image — Old Transformers

`nvcr.io/nvidia/vllm:26.04-py3` (Apr 2026) has Blackwell support but Transformers too old to recognize `gemma4` architecture.

### Reddit Confirmation

[Reddit post](https://www.reddit.com/r/learnmachinelearning/comments/1t5ueli/gb10dgx_spark_reality_check_gemma4_mtp_gets_7580/) confirms:
- 75-80 tok/s ceiling on DGX Spark (bare-minimum config)
- NVFP4 caps at 50-52 tok/s (Marlin decompression)
- `gemma4-0505-arm64-cu130` preview image needed
- PR #41745 fix required for MTP

### Article Reference

[ai-muninn article](https://ai-muninn.com/en/blog/dgx-spark-gemma4-mtp-108-toks): 108 tok/s single-stream with `gemma4-0505` preview image + patched `gemma4_mtp.py`. Not reproducible with newer builds.


## Chat Template Update (PR #45553, June 16)

The Gemma4 tool chat template was significantly updated in PR #45553:
- Added `{{- bos_token -}}` natively (no longer needs manual prepend)
- Added `preserve_thinking` parameter for reasoning across tool-call turns
- Fixed offline parser truncation and `adjust_request` token leak
- Added `image_url` and `input_audio` type support (OpenAI format)
- Better `None`/null handling for tool arguments
- O(1) continuation detection instead of O(n) backward scan

Downloaded from: `https://raw.githubusercontent.com/vllm-project/vllm/6607a80d/examples/tool_chat_template_gemma4.jinja`

Path: `/opt/atom/models/tool_chat_template_gemma4.jinja`

## Files

| File | Path | Size |
|---|---|---|
| FP8 model | `/opt/atom/models/gemma-4-26b-a4b-it-fp8-dynamic/` | 27 GB |
| MTP assistant | `/opt/atom/models/gemma-4-26b-a4b-it-assistant/` | 872 MB |
| Built image | `vllm-node-tf5:latest` | 19 GB |
| Build source | `/opt/atom/build/spark-vllm-docker/` | — |
