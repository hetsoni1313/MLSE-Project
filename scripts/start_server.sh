#!/bin/bash
# Start llama.cpp server for local model inference
set -e

MODEL_DIR="${MODEL_CACHE_DIR:-$HOME/.cache/llmops-governance/models}"
MODEL_FILE="${1:-qwen2.5-1.5b-instruct-q4_k_m.gguf}"
MODEL_PATH="$MODEL_DIR/$MODEL_FILE"
PORT="${LLAMA_PORT:-8081}"
THREADS="${LLAMA_THREADS:-4}"
CTX_SIZE="${LLAMA_CTX_SIZE:-2048}"

if [ ! -f "$MODEL_PATH" ]; then
    echo "❌ Model not found: $MODEL_PATH"
    echo "   Please download or convert your model first."
    echo "   Expected path: $MODEL_PATH"
    exit 1
fi

echo "🚀 Starting llama.cpp server..."
echo "   Model: $MODEL_PATH"
echo "   Port: $PORT"
echo "   Threads: $THREADS"
echo "   Context: $CTX_SIZE"

# Detect llama-server binary
LLAMA_BIN=""
for bin in llama-server llama-cli server; do
    if command -v "$bin" &>/dev/null; then
        LLAMA_BIN="$bin"
        break
    fi
done

if [ -z "$LLAMA_BIN" ]; then
    echo "❌ llama.cpp server binary not found."
    echo "   Install: brew install llama.cpp"
    exit 1
fi

exec "$LLAMA_BIN" \
    --model "$MODEL_PATH" \
    --host 0.0.0.0 \
    --port "$PORT" \
    --ctx-size "$CTX_SIZE" \
    --threads "$THREADS" \
    --n-predict 30

