# CUDA Graphs on Blackwell GB10

## Why CUDA Graphs Matter

Every token generation step in vLLM launches hundreds of small GPU kernels
(one per transformer layer per operation). Without CUDA graphs, each kernel
launch requires a CPU-to-GPU round-trip through the driver stack, adding
~5-10 µs of overhead per call.

On a 26B Gemma4 model with ~28 layers × ~12 kernels/layer, that's **~336
kernel launches per token** — each with its own launch overhead.

## Without CUDA graphs (--enforce-eager)

```
Token N:
  CPU:  launch rms_norm → launch q_proj → launch k_proj → ...
  GPU:  [running]        [running]        [running]
         ↑ 5-10µs gap    ↑ 5-10µs gap    ↑ 5-10µs gap
```

Each launch is synchronous from the CPU's perspective — the driver can't
return until the kernel is queued. At 336 launches × ~10 µs = **3.4 ms of
pure overhead per token**, this caps throughput at ~22 tok/s on Blackwell
SM121 with `--enforce-eager`.

## With CUDA graphs

CUDA graphs **record** the entire sequence of kernel launches into a single
graph object, then **replay** it with one API call:

```
[Capture phase] — one-time, ~2 seconds
  Record all 336 kernel launches into a graph

[Replay phase] — every token
  CPU:  replay_graph()
  GPU:  [rms_norm → q_proj → k_proj → ... → lm_head]
         ↑ one API call for all 336 kernels
```

The CPU overhead drops from 336 calls (~3.4 ms) to **1 call (~10 µs)**.

## Real-world impact

| Config | CUDA graphs | Tok/s | Limiting factor |
|---|---|---|---|
| FP8 + enforce-eager | ❌ | ~22 | Kernel launch overhead |
| FP8 + CUDA graphs | ✅ | 47-54* | Memory bandwidth |
| **NVFP4 + Marlin** | **✅** | **51** | **Memory bandwidth** |

*FP8 + CUDA graphs crashes on Blackwell SM121 with CUTLASS error — no
workaround exists (kernel compatibility issue).

The **RedHatAI NVFP4** model (16 GB, 4-bit NVFP4 quantization) works with
CUDA graphs on SM121 via the Marlin software-decompression backend, avoiding
the CUTLASS crash entirely.

## Caveats

- **Capture is fragile**: Any change to tensor shapes, batch size, or
  sequence length requires recapture. vLLM handles this by capturing
  multiple graph sizes on startup.
- **Memory trade-off**: CUDA graphs reserve ~0.06 GiB of GPU memory for
  captured graphs (small cost for 2.3× speedup).
- **Marlin backend**: The `VLLM_NVFP4_GEMM_BACKEND=marlin` env var forces
  software decompression of NVFP4 weights to BF16 at runtime, enabling
  CUDA graph capture where the default FlashInferCutlass backend would
  fail on SM121.

## References

- [vLLM CUDA graph docs](https://docs.vllm.ai/en/latest/performance/cuda_graphs.html)
- [NVIDIA CUDA Graphs](https://developer.nvidia.com/blog/cuda-graphs/)
- [spark-vllm-docker](https://github.com/eugr/spark-vllm-docker) — Blackwell
  compatibility patches
