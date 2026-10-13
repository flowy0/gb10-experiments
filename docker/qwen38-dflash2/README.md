# Main model image — Qwen3.8-27B NVFP4 + DFlash2

Build recipe for `weschera/qwen38-27b-dflash2:2026-08-19`, the SGLang image that serves the main model
(`radixark-qwen38-27b-nvfp4-dflash2-262k-think`, compose service `sglang-qwen38`).
See [../../docs/guides/main-model.md](../../docs/guides/main-model.md) for the serving config.

> **Why this directory exists.** The image was **built locally and never pushed to a registry**
> (`docker image inspect` reports no `RepoDigests`). Before 2026-10-13 the only record of how to rebuild it
> was a prose sentence in the CHANGELOG. A `docker image prune -a`, a disk failure, or a bad layer would
> have destroyed the main model with no way back. This Dockerfile and patch close that gap.

## Provenance

| | |
|---|---|
| Image | `weschera/qwen38-27b-dflash2:2026-08-19` |
| Image ID | `sha256:5c188f73b0fd78a701706ba72013f6026fdc733982a0fd011f1bfd6435da052d` |
| Size / built | 38.7 GB / 2026-08-20 |
| Base | `lmsysorg/sglang@sha256:febfb971c7352570fc445c466ebd6ffc9d896024958e544a60f2137fd85856b1` (`:qwen38-27b`) |
| SGLang source | upstream `e5a3e4d30fa7abda95bafd2d697f9f9c48566114` — *"use get_parallel().tp_size in dflash2 selector"* (2026-08-18) |
| Overlay | `patches/quantized-lm-head.patch` (2449 B) |
| Runtime version | `sglang 0.0.0.dev0+qwen38.27b.g561c8f3` |

### What the patch does

Lets the DFlash2 candidate selector run against a **quantized target `lm_head`** instead of demanding a
dense FP16/BF16/FP32 head. The RadixArk NVFP4 checkpoint has a quantized head, so without this the selector
raises `DFlash2 selector requires a dense FP16/BF16/FP32 target lm_head.`

The patched path:
- refuses to run at `tp != 1` (single-GPU only — this box is a single DGX Spark, so fine);
- requires the head to expose a callable `quant_method.apply`;
- runs the head **outside** draft CUDA-graph capture and chunks it at 256 rows, bounding the temporary
  logits allocation for larger selector batches;
- trims logits to `org_vocab_size` when the head is padded.

It touches exactly one file: `python/sglang/srt/models/dflash.py` (assert-becomes-branch around line 962).

### ⚠️ The version string is misleading

`sglang 0.0.0.dev0+qwen38.27b.g561c8f3` does **not** identify the source commit.

- `g561c8f3` is the **base image's** `SGLANG_VERSION` build stamp, set when the RadixArk base was built.
- It is **not** a commit in `sgl-project/sglang` — `GET /repos/sgl-project/sglang/commits/561c8f3` returns 404.
- The install is *editable* from a plain directory with no `.git` (`direct_url.json` →
  `file:///sgl-workspace/sglang/python`), so `setuptools_scm` could not resolve anything and fell back to
  the `SETUPTOOLS_SCM_PRETEND_VERSION` the base build set.

**The source commit is `e5a3e4d3`.** Use that for provenance, not the version string.

## Build

```bash
cd docker/qwen38-dflash2
docker build -t weschera/qwen38-27b-dflash2:2026-08-19 .
```

Requires the base image locally (~30 GB) and roughly 60 GB of free disk. The `RUN` step clones SGLang
(blobless) and copies ~56 MB of Python source; the heavy CUDA/kernel compilation already happened in the
base image, so this overlay build is comparatively quick.

The `FROM` is pinned by the base's **manifest-list digest**, so it resolves correctly on arm64 (DGX Spark)
and amd64 alike.

## Verification

The recipe was reconstructed from `docker history`, then checked as follows:

1. **Layer commands** — every `ARG`/`COPY`/`RUN`/`LABEL` is the verbatim buildkit command from
   `docker history --no-trunc` of the running image.
2. **Patch identification** — computed `git hash-object` for all 4488 non-`__pycache__` files under the
   container's `/sgl-workspace/sglang/python/sglang` and compared them against the recursive git tree of
   upstream at `e5a3e4d3` (`GET /git/trees/<sha>?recursive=1`). Exactly **one** file differed:
   `srt/models/dflash.py`. (A second apparent diff, `srt/mem_cache/cpp_radix_tree/.clang-format`, is a
   base-image leftover: upstream stores it as a symlink, the container has a real file, and `cp -a` does
   not delete base-only paths. It is byte-identical to the base image's copy, so it is not part of the patch.)
3. **Patch size** — the reconstruction is **2449 bytes** against the original `COPY` layer's **2450 bytes**;
   the 1-byte difference is the trailing-newline convention.
4. **Applies cleanly** — `git apply --check` passes against a pristine `e5a3e4d3` checkout.

## Upgrading

DFlash2 was **merged upstream** as PR #35371 on 2026-08-19, so this overlay's reason to exist shrinks over
time. When upgrading, note that a substantial set of DFlash-family fixes landed on `main` during Oct 2026
after this build — most relevantly `#43290` (hold back decode rows when a mixed step does not fit the KV
pool) and `#41736` (keep grouped-conv taps inside each request's block so NaN/Inf cannot leak across
requests). See the CHANGELOG entry for 2026-10-13 for the full list.

After any rebuild, re-check draft acceptance — it should sit around **3.6–3.9 tokens/step**. A quantized
DFlash2 draft can silently collapse to ~1.0 with no error (upstream issue #39087); this build is unaffected,
but it is the failure mode to watch for.
