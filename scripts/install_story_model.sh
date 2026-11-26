#!/usr/bin/env bash
set -euo pipefail

model_dir=$1
mkdir -p "$model_dir"
llama_hash=27e18f608c7cd1e2f86d70f91bde4299e795113c0065322f6339cbe5135e79c2
model_hash=3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597
llama_url=https://github.com/ggml-org/llama.cpp/releases/download/b12776/llama-b12776-bin-ubuntu-x64.tar.gz
model_url=https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/resolve/a06e946bb6b655725eafa393f4a9745d460374c9/Qwen3-4B-Instruct-2507-Q4_K_M.gguf

fetch_verified() {
  local destination=$1 url=$2 expected=$3
  if ! printf '%s  %s\n' "$expected" "$destination" | sha256sum --check --status; then
    curl --fail --silent --show-error --location --retry 1 --max-time 240 "$url" -o "$destination.part"
    printf '%s  %s\n' "$expected" "$destination.part" | sha256sum --check --status
    mv "$destination.part" "$destination"
  fi
}

fetch_verified "$model_dir/llama.tar.gz" "$llama_url" "$llama_hash"
fetch_verified "$model_dir/model.gguf" "$model_url" "$model_hash"
tar -xf "$model_dir/llama.tar.gz" -C "$model_dir"
