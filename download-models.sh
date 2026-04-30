#!/usr/bin/env bash
set -euo pipefail

MODEL_DIR="/opt/atom/models"
mkdir -p "$MODEL_DIR"
cd "$MODEL_DIR"

echo "Downloading model files to: $MODEL_DIR"

download_file() {
  local repo="$1"
  local file="$2"

  if find "$MODEL_DIR" -type f -name "$file" | grep -q .; then
    echo "Already exists: $file"
    return
  fi

  echo "Downloading: $repo / $file"
  hf download "$repo" "$file" --local-dir "$MODEL_DIR"
}

download_include() {
  local repo="$1"
  local target_dir="$2"
  local pattern="$3"

  mkdir -p "$MODEL_DIR/$target_dir"

  if find "$MODEL_DIR/$target_dir" -type f -name "*.gguf" | grep -q .; then
    echo "Already has GGUF files: $target_dir"
    return
  fi

  echo "Downloading from repo: $repo"
  echo "Include pattern: $pattern"
  echo "Target: $MODEL_DIR/$target_dir"

  hf download "$repo" \
    --include "$pattern" \
    --local-dir "$MODEL_DIR/$target_dir"
}

# =========================
# Baseline: Qwen2.5 Coder 14B
# =========================

download_file \
  "bartowski/Qwen2.5-Coder-14B-Instruct-GGUF" \
  "Qwen2.5-Coder-14B-Instruct-Q4_K_M.gguf"

# =========================
# Gemma 4 E4B
# =========================

download_file \
  "bartowski/google_gemma-4-E4B-it-GGUF" \
  "google_gemma-4-E4B-it-Q4_K_M.gguf"

download_file \
  "bartowski/google_gemma-4-E4B-it-GGUF" \
  "google_gemma-4-E4B-it-Q5_K_M.gguf"

# =========================
# Qwen3.5 9B
# =========================

download_include \
  "bartowski/Qwen_Qwen3.5-9B-GGUF" \
  "qwen3.5-9b-gguf" \
  "*Q4_K_M*.gguf"

# =========================
# Qwen3.6 27B
# =========================

download_include \
  "bartowski/Qwen_Qwen3.6-27B-GGUF" \
  "qwen3.6-27b-gguf" \
  "*Q4_K_M*.gguf"

echo
echo "Available GGUF files:"
find "$MODEL_DIR" -iname "*.gguf" -ls