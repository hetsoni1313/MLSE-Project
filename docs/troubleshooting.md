# Troubleshooting

## Common Issues

### Gateway won't start
- Check Python version: `python3 --version` (need 3.11+)
- Install dependencies: `pip install -e ".[dev]"`
- Check port availability: `lsof -i :8000`

### Database connection error
- For SQLite (default): ensure `data/` directory exists
- For PostgreSQL: check `DATABASE_URL` in `.env`
- Run `docker compose up postgres` if using Docker

### "No API key configured"
- The gateway uses `MockBaselineBackend` without an API key
- Set `OPENAI_API_KEY` in `.env` for real API calls
- Mock results are clearly labeled in responses

### Tests failing
- Run from project root: `cd MLSE-Project && pytest tests/ -v`
- Ensure virtual environment is active: `source venv/bin/activate`
- Check for port conflicts on 8000, 8081, 8501

### llama.cpp server not starting
- Install: `brew install llama.cpp`
- Check model file exists: `ls ~/.cache/llmops-governance/models/`
- Verify GGUF file: `file path/to/model.gguf`

### Dashboard shows empty
- Ensure gateway is running and has processed requests
- Check database path matches between gateway and dashboard
- Send test traffic: `curl -X POST http://localhost:8000/classify -H 'Content-Type: application/json' -d '{"message": "test"}'`

### Import errors
- Install in editable mode: `pip install -e .`
- Check Python path includes project root

### Docker build fails on Apple Silicon
- Use ARM64-compatible base images (default in compose.yaml)
- Ensure Docker Desktop has sufficient memory allocated

## Getting Help
- Check `docs/` directory for detailed documentation
- Run `bash scripts/healthcheck.sh` to diagnose service status
- Review structured logs in terminal output

