##From https://github.com/mARTin-B78/dgx-spark_lite-llm_llama-swap_vllm_llama-cpp_ollama/tree/main/llama-cpp

# lama-swap.Dockerfile


# g@flint:/opt/atom/llama-swap$ docker run --rm ghcr.io/ggml-org/llama.cpp:server-cuda --version
# load_backend: loaded CPU backend from /app/libggml-cpu-armv8.6_[2.so](http://2.so)
# version: 8967 (fc2b0053f)
# built with GNU 14.2.0 for Linux aarch64

FROM ubuntu:22.04

ARG LLAMA_SWAP_VERSION=v217

# Install dependencies AND docker.io so llama-swap can manage containers
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates \
    wget \
    curl \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Download the latest tagged release of llama-swap
RUN mkdir -p /tmp/llama-swap-build && \
    cd /tmp/llama-swap-build && \
    wget -q https://github.com/mostlygeek/llama-swap/releases/download/${LLAMA_SWAP_VERSION}/llama-swap_${LLAMA_SWAP_VERSION#v}_linux_arm64.tar.gz && \
    tar -xzf llama-swap_${LLAMA_SWAP_VERSION#v}_linux_arm64.tar.gz && \
    mv llama-swap /usr/bin/llama-swap && \
    chmod +x /usr/bin/llama-swap && \
    cd / && \
    rm -rf /tmp/llama-swap-build

WORKDIR /app

EXPOSE 8080

ENTRYPOINT ["/usr/bin/llama-swap"]
