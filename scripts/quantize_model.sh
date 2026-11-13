#!/bin/bash
# Quantize GGUF model to Q4_K_M (and optionally Q8_0)
set -e

MODEL_DIR="${MODEL_CACHE_DIR:-$HOME/.cache/llmops-governance/models}"
INPUT_FILE="${1:-$MODEL_DIR/qwen2.5-1.5b-instruct.gguf}"
MODEL_NAME="qwen2.5-1.5b-instruct"

if [ ! -f "$INPUT_FILE" ]; then
    echo "❌ Input GGUF not found: $INPUT_FILE"
    echo "   Run convert_to_gguf.sh first."
    exit 1
fi

# Find llama-quantize binary
QUANTIZE_BIN=""
for bin in llama-quantize quantize; do
    if command -v "$bin" &>/dev/null; then
        QUANTIZE_BIN="$bin"
        break
    fi
done

if [ -z "$QUANTIZE_BIN" ]; then
    echo "❌ llama-quantize not found. Install llama.cpp: brew install llama.cpp"
    exit 1
fi

# Q4_K_M (required)
OUTPUT_Q4="$MODEL_DIR/${MODEL_NAME}-q4_k_m.gguf"
echo "🔄 Quantizing to Q4_K_M..."
"$QUANTIZE_BIN" "$INPUT_FILE" "$OUTPUT_Q4" Q4_K_M
echo "✅ Q4_K_M: $OUTPUT_Q4 ($(du -h "$OUTPUT_Q4" | cut -f1))"

# Q8_0 (optional)
if [ "${QUANTIZE_Q8:-false}" = "true" ]; then
    OUTPUT_Q8="$MODEL_DIR/${MODEL_NAME}-q8_0.gguf"
    echo "🔄 Quantizing to Q8_0..."
    "$QUANTIZE_BIN" "$INPUT_FILE" "$OUTPUT_Q8" Q8_0
    echo "✅ Q8_0: $OUTPUT_Q8 ($(du -h "$OUTPUT_Q8" | cut -f1))"
fi

echo ""
echo "📦 Model manifest:"
echo "   Model: $MODEL_NAME"
echo "   Q4_K_M: $OUTPUT_Q4"
ls -lh "$OUTPUT_Q4"

