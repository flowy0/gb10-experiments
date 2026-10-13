# Qwen3.8-27B NVFP4 + DFlash2 runtime for one DGX Spark (main model image).
#
# Python-source overlay on the stock RadixArk `qwen38-27b` base image: check out
# upstream SGLang at the pinned DFlash2 commit, apply the quantized-lm-head
# patch, and copy the patched tree over the base's python/sglang. `cp -a` merges
# and overwrites, so base-only files are left in place.
#
# This file was reconstructed 2026-10-13 from `docker history` of the running
# image (weschera/qwen38-27b-dflash2:2026-08-19, built 2026-08-20) — the original
# build context was gone. Every RUN/COPY/ARG/LABEL below is the verbatim layer
# command, de-quoted from the buildkit history.
#
# The patch was recovered byte-exact (2449 B vs the original COPY layer's
# 2450 B — the 1-byte delta is the trailing-newline convention) by diffing the
# container's srt/models/dflash.py against upstream at the pinned commit. See
# README.md for the verification method.
#
# Build (see README.md for the full procedure and verification steps):
#   cd docker/qwen38-dflash2
#   docker build -t weschera/qwen38-27b-dflash2:2026-08-19 .
#
# The base image must be present locally (~30 GB). Builds C++/CUDA extensions,
# so expect a long build and ~60 GB of free disk.

FROM lmsysorg/sglang@sha256:febfb971c7352570fc445c466ebd6ffc9d896024958e544a60f2137fd85856b1

ARG SGLANG_DFLASH_COMMIT=e5a3e4d30fa7abda95bafd2d697f9f9c48566114

COPY patches/quantized-lm-head.patch /tmp/quantized-lm-head.patch

RUN git clone --filter=blob:none https://github.com/sgl-project/sglang.git /tmp/sglang-source \
    && cd /tmp/sglang-source \
    && git checkout "$SGLANG_DFLASH_COMMIT" \
    && git apply /tmp/quantized-lm-head.patch \
    && cp -a python/sglang/. /sgl-workspace/sglang/python/sglang/ \
    && rm -rf /tmp/sglang-source /tmp/quantized-lm-head.patch

LABEL org.opencontainers.image.title=qwen38-27b-nvfp4-dflash2-dgx-spark \
      org.opencontainers.image.description="Pinned Qwen3.8-27B NVFP4 + DFlash2 runtime for one DGX Spark" \
      io.weschera.sglang-source=$SGLANG_DFLASH_COMMIT
