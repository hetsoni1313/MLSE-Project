# Local Model Serving

This module manages the local fine-tuned model served via llama.cpp.

## Setup

1. **Fine-tune the model** using the Colab notebook at `training/notebooks/colab_finetuning.ipynb`
2. **Download the merged model** from Colab
3. **Convert to GGUF**: `bash scripts/convert_to_gguf.sh ./merged_model`
4. **Quantize**: `bash scripts/quantize_model.sh`
5. **Start server**: `bash scripts/start_server.sh`

## Model Storage

Models are stored outside the Git repository at:
```
~/.cache/llmops-governance/models/
```

Override with `MODEL_CACHE_DIR` environment variable.

## Server Configuration

| Setting | Default | Env Var |
|---------|---------|---------|
| Port | 8081 | `LLAMA_PORT` |
| Threads | 4 | `LLAMA_THREADS` |
| Context Size | 2048 | `LLAMA_CTX_SIZE` |

## API Compatibility

The llama.cpp server exposes an OpenAI-compatible API:
- `POST /v1/chat/completions`
- `GET /health`

The gateway's `LocalModelBackend` communicates through this API.

