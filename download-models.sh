#!/usr/bin/env bash
set -euo pipefail

MODEL_DIR="/opt/atom/models"
mkdir -p "$MODEL_DIR"

echo "Downloading model files to: $MODEL_DIR"
echo

download_exact() {
  local repo="$1"
  local file="$2"
  local target_dir="$3"

  mkdir -p "$MODEL_DIR/$target_dir"

  if [ -f "$MODEL_DIR/$target_dir/$file" ]; then
    echo "Already exists: $target_dir/$file"
    return
  fi

  echo "Downloading: $repo / $file"
  echo "Target: $MODEL_DIR/$target_dir"
  hf download "$repo" "$file" --local-dir "$MODEL_DIR/$target_dir"
  echo
}

download_root_exact() {
  local repo="$1"
  local file="$2"

  if [ -f "$MODEL_DIR/$file" ]; then
    echo "Already exists: $file"
    return
  fi

  echo "Downloading: $repo / $file"
  echo "Target: $MODEL_DIR"
  hf download "$repo" "$file" --local-dir "$MODEL_DIR"
  echo
}

# ============================================================
# Qwen2.5 Coder family
# ============================================================

# Existing/root legacy path used by current llama-swap config:
# /opt/atom/models/Qwen2.5-Coder-14B-Instruct-Q4_K_M.gguf
download_root_exact \
  "bartowski/Qwen2.5-Coder-14B-Instruct-GGUF" \
  "Qwen2.5-Coder-14B-Instruct-Q4_K_M.gguf"

download_exact \
  "bartowski/Qwen2.5-Coder-7B-Instruct-GGUF" \
  "Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf" \
  "qwen2.5-coder-7b-gguf"

# ============================================================
# Qwen3 / Qwen3.5 / Qwen3.6 family
# ============================================================

download_exact \
  "bartowski/Qwen_Qwen3.5-9B-GGUF" \
  "Qwen_Qwen3.5-9B-Q4_K_M.gguf" \
  "qwen3.5-9b-gguf"

# Ambiguous old Qwen3.5 27B folder exists, but keep Unsloth explicit copy.
download_exact \
  "unsloth/Qwen3.5-27B-GGUF" \
  "Qwen3.5-27B-Q4_K_M.gguf" \
  "unsloth-qwen3.5-27b-gguf"

download_exact \
  "unsloth/Qwen3.6-27B-GGUF" \
  "Qwen3.6-27B-Q4_K_M.gguf" \
  "qwen3.6-27b-gguf"

download_exact \
  "unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF" \
  "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf" \
  "qwen3-coder-30b-a3b-gguf"

# Optional / previously explored. Keep only if you actually use it.
# download_exact \
#   "Qwen/Qwen3-Coder-Next-GGUF" \
#   "<ACTUAL_FILENAME>.gguf" \
#   "qwen3-coder-next-gguf"

# ============================================================
# Gemma 3 family
# ============================================================

download_root_exact \
  "bartowski/google_gemma-3-4b-it-GGUF" \
  "google_gemma-3-4b-it-Q4_K_M.gguf"

download_exact \
  "unsloth/gemma-3-12b-it-GGUF" \
  "gemma-3-12b-it-Q4_K_M.gguf" \
  "unsloth-gemma-3-12b-it-gguf"

# Optional QAT candidate. Verify filename before enabling.
# download_exact \
#   "unsloth/gemma-3-4b-it-qat-int4-GGUF" \
#   "<ACTUAL_FILENAME>.gguf" \
#   "unsloth-gemma-3-4b-it-qat-int4-gguf"

# ============================================================
# Gemma 4 family
# ============================================================

# Existing Bartowski Gemma 4 E4B files
download_root_exact \
  "bartowski/google_gemma-4-E4B-it-GGUF" \
  "google_gemma-4-E4B-it-Q4_K_M.gguf"

download_root_exact \
  "bartowski/google_gemma-4-E4B-it-GGUF" \
  "google_gemma-4-E4B-it-Q5_K_M.gguf"

# New Unsloth Gemma 4 E4B
download_exact \
  "unsloth/gemma-4-E4B-it-GGUF" \
  "gemma-4-E4B-it-Q4_K_M.gguf" \
  "unsloth-gemma-4-e4b-it-gguf"

# New Unsloth Gemma 4 26B-A4B
download_exact \
  "unsloth/gemma-4-26B-A4B-it-GGUF" \
  "gemma-4-26B-A4B-it-UD-Q4_K_M.gguf" \
  "unsloth-gemma-4-26b-a4b-it-gguf"

# ============================================================
# Ministral 3 family
# ============================================================

download_exact \
  "bartowski/mistralai_Ministral-3-3B-Instruct-2512-GGUF" \
  "mistralai_Ministral-3-3B-Instruct-2512-Q6_K.gguf" \
  "ministral3-3b-instruct-2512-gguf"

download_exact \
  "bartowski/mistralai_Ministral-3-8B-Instruct-2512-GGUF" \
  "mistralai_Ministral-3-8B-Instruct-2512-Q5_K_M.gguf" \
  "ministral3-8b-instruct-2512-gguf"

# ============================================================
# Devstral family
# ============================================================

download_exact \
  "bartowski/mistralai_Devstral-Small-2-24B-Instruct-2512-GGUF" \
  "mistralai_Devstral-Small-2-24B-Instruct-2512-Q4_K_M.gguf" \
  "devstral-small-2-24b-2512-gguf"

# Older Devstral Small 2507, already present in your tree.
# Keep this only if you still want the older comparison model.
download_exact \
  "bartowski/Devstral-Small-2507-GGUF" \
  "Devstral-Small-2507-Q4_K_M.gguf" \
  "devstral-small-2507-gguf"

# ============================================================
# Carnice
# ============================================================

# Already deprioritised, but included for reproducibility.
download_exact \
  "bartowski/carnice-v2-27b-GGUF" \
  "carnice-v2-27b-Q2_K.gguf" \
  "carnice-v2-27b-gguf"

# ============================================================
# Small legacy Gemma 2
# ============================================================

# Already present in root.
# Repo/source may vary; keep disabled unless you know the source repo.
# download_root_exact \
#   "<SOURCE_REPO>" \
#   "gemma-2-2b-it-Q4_K_M.gguf"

echo
echo "Available GGUF files:"
find "$MODEL_DIR" -maxdepth 4 -type f -iname "*.gguf" -printf "%p\n" | sort

echo
echo "Done."