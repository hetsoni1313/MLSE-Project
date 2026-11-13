#!/bin/bash
# Convert merged model to GGUF format
set -e

MERGED_DIR="${1:-./merged_model}"
OUTPUT_DIR="${MODEL_CACHE_DIR:-$HOME/.cache/llmops-governance/models}"
MODEL_NAME="qwen2.5-1.5b-instruct"

mkdir -p "$OUTPUT_DIR"

if [ ! -d "$MERGED_DIR" ]; then
    echo "❌ Merged model directory not found: $MERGED_DIR"
    echo "   Run the Colab notebook first and download the merged model."
    exit 1
fi

# Check disk space (need ~6GB free)
FREE_GB=$(df -BG "$OUTPUT_DIR" | tail -1 | awk '{print $4}' | tr -d 'G')
if [ "$FREE_GB" -lt 6 ]; then
    echo "⚠️  Low disk space: ${FREE_GB}GB free. Need ~6GB."
fi

echo "🔄 Converting to GGUF format..."
echo "   Input: $MERGED_DIR"
echo "   Output: $OUTPUT_DIR/${MODEL_NAME}.gguf"

# Use llama.cpp's convert script
if command -v python3 &>/dev/null; then
    # Try llama.cpp convert_hf_to_gguf.py
    CONVERT_SCRIPT=""
    for path in \
        "$(brew --prefix 2>/dev/null)/share/llama.cpp/convert_hf_to_gguf.py" \
        "$HOME/llama.cpp/convert_hf_to_gguf.py" \
        "./llama.cpp/convert_hf_to_gguf.py"; do
        if [ -f "$path" ]; then
            CONVERT_SCRIPT="$path"
            break
        fi
    done

    if [ -n "$CONVERT_SCRIPT" ]; then
        python3 "$CONVERT_SCRIPT" "$MERGED_DIR" --outfile "$OUTPUT_DIR/${MODEL_NAME}.gguf" --outtype f16
        echo "✅ Converted to: $OUTPUT_DIR/${MODEL_NAME}.gguf"
    else
        echo "❌ convert_hf_to_gguf.py not found."
        echo "   Install llama.cpp and ensure the convert script is available."
        echo "   See: https://github.com/ggerganov/llama.cpp"
    fi
else
    echo "❌ Python3 not found"
fi

