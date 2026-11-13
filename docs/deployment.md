# Deployment Guide

## Local Development (macOS Apple Silicon)

### Prerequisites
- Python 3.11+
- (Optional) llama.cpp: `brew install llama.cpp`
- (Optional) Docker Desktop for containerized deployment

### Quick Setup
```bash
python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
python scripts/download_data.py
python scripts/prepare_data.py
cp .env.example .env
```

### Running Services
```bash
# Terminal 1: Gateway
uvicorn gateway.main:app --port 8000 --reload

# Terminal 2: Dashboard
streamlit run dashboard/app.py --server.port 8501

# Terminal 3 (optional): llama.cpp server
bash scripts/start_server.sh
```

## Docker Compose

### Default Profile (gateway + postgres + dashboard)
```bash
docker compose up -d
```

### Full Profile (+ llama.cpp server)
```bash
MODEL_CACHE_DIR=/path/to/models docker compose --profile full up -d
```

### Environment Variables
Copy `.env.example` to `.env` and configure:
- `OPENAI_API_KEY` — for real baseline evaluation
- `ADMIN_API_KEY` — for admin endpoint authentication
- `DATABASE_URL` — database connection string
- `MODEL_CACHE_DIR` — path to GGUF model files

## Resource Requirements

| Service | RAM | CPU |
|---------|-----|-----|
| Gateway | 256 MB | 1 core |
| PostgreSQL | 256 MB | 1 core |
| Dashboard | 256 MB | 1 core |
| llama.cpp (Q4_K_M) | 2-4 GB | 4 cores |
| **Total** | **~4 GB** | — |

Suitable for a MacBook Air M4 with 16 GB unified memory.

