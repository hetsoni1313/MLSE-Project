# Implementation Decisions

## 1. Python 3.13 (not 3.12)
The developer machine has Python 3.13.5 installed; Python 3.12 is not available. `pyproject.toml` requires `>=3.11` for broad compatibility.

## 2. SQLite as Default Database
PostgreSQL is the production database (via Docker Compose), but SQLite is used by default for development. This avoids requiring Docker/PostgreSQL for local development. The `DatabaseManager` auto-detects the backend from the URL.

## 3. Mock Baseline Backend
When no `OPENAI_API_KEY` is configured, the gateway uses `MockBaselineBackend` with deterministic keyword-based predictions. This is clearly labeled in responses and logs. Real API results are never fabricated.

## 4. Async-First Design
The gateway uses async throughout (FastAPI, httpx, SQLAlchemy async, asyncio). Non-blocking request logging prevents database writes from blocking responses.

## 5. Pydantic v2 for Validation
All request/response schemas use Pydantic v2 for runtime type validation, serialization, and documentation via OpenAPI.

## 6. Deterministic Sticky Routing
SHA-256 hash of user_id mapped to [0, 100) bucket provides deterministic, reproducible routing assignment without random state.

## 7. Rollback Safety Guards
- Accuracy rollback requires `min_labelled_samples` ground-truth labels (prevents false triggers)
- Duplicate rollback prevention via `is_rolled_back` flag
- Recovery only through explicit admin action (not automatic)
- All events persisted to database

## 8. Fault Injection Isolation
Fault injection is disabled by default (`FAULT_INJECTION_ENABLED=false`). Even when enabled, it requires explicit API calls to toggle specific faults. It wraps the local backend only.

## 9. Cost Per Query Calculation
API costs use actual token counts from responses. Local costs use a configurable machine-cost-per-hour model divided by queries-per-hour throughput.

## 10. Model Storage Outside Git
GGUF files (~1-2GB) are stored at `~/.cache/llmops-governance/models/` and excluded via `.gitignore`. This prevents bloating the repository.

