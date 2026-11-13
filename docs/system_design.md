# System Design Document

## LLMOps Cost & Latency Governance Platform

### 1. System Overview

This platform provides an intelligent gateway for routing Banking77 intent classification
requests between a commercial LLM API (GPT-4o-mini) and a locally fine-tuned model
(Qwen2.5-1.5B-Instruct, quantized to Q4_K_M via llama.cpp). The system continuously
measures accuracy, latency, cost, and throughput to enable data-driven model promotion.

### 2. Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENT / TRAFFIC SIMULATOR                │
│                     (loadtest/replay.py — async)                 │
└─────────────────────────────┬────────────────────────────────────┘
                              │ POST /classify
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                       FASTAPI GATEWAY (:8000)                    │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐ │
│  │   Routing    │  │  Resilience │  │     Request Logger       │ │
│  │   Engine     │  │  ├ Fallback │  │  (async, non-blocking)   │ │
│  │  ├ Weighted  │  │  ├ Circuit  │  └──────────────────────────┘ │
│  │  ├ Sticky    │  │  │ Breaker  │                               │
│  │  ├ Shadow    │  │  └ Rollback │  ┌──────────────────────────┐ │
│  │  └ Canary    │  │    Monitor  │  │   Metrics Collector      │ │
│  └─────────────┘  └─────────────┘  │   (in-memory, windowed)  │ │
│                                     └──────────────────────────┘ │
│      ┌────────────────┐     ┌────────────────┐                   │
│      │ Baseline API   │     │ Local Model    │                   │
│      │ (OpenAI/Mock)  │     │ (llama.cpp)    │                   │
│      └───────┬────────┘     └───────┬────────┘                   │
└──────────────┼──────────────────────┼────────────────────────────┘
               │                      │
               ▼                      ▼
┌──────────────────────────────────────────────────────────────────┐
│                  METRICS DATABASE                                │
│            SQLite (dev) / PostgreSQL (prod)                       │
│                                                                  │
│  Tables: request_logs, experiment_runs, rollback_events,         │
│          evaluation_summaries, routing_config_history,            │
│          cost_assumptions                                        │
└──────────────────────────┬───────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼                         ▼
┌──────────────────────┐  ┌──────────────────────────┐
│  STREAMLIT DASHBOARD │  │   EVALUATION ENGINE      │
│  (:8501, 6 pages)    │  │   (offline analysis)     │
│  ├ Executive Overview│  │   ├ Accuracy / F1        │
│  ├ Model Performance │  │   ├ Cost Calculator      │
│  ├ Latency/Throughput│  │   ├ Break-even Analysis  │
│  ├ Cost Intelligence │  │   ├ Sensitivity Analysis  │
│  ├ Routing/Reliability│ │   └ Promotion Gate       │
│  └ Experiments       │  └──────────────────────────┘
└──────────────────────┘
```

### 3. Component Design

#### 3.1 Routing Engine (`gateway/routing/`)

The routing engine supports four strategies:

| Mode | Description | Use Case |
|------|-------------|----------|
| `baseline` | 100% commercial API | Default safe mode |
| `weighted` | Configurable split (e.g. 70/30) | Gradual migration |
| `shadow` | Baseline serves, local runs silently | Pre-deployment evaluation |
| `canary` | Staged rollout (5% → 25% → 50% → 100%) | Progressive deployment |

**Sticky routing**: Uses SHA-256 hash of user_id to ensure the same user always
hits the same backend under unchanged percentages. This prevents inconsistent
behavior during A/B testing.

**Thread safety**: All config updates are protected by `threading.RLock`.

#### 3.2 Resilience Layer (`gateway/resilience/`)

| Component | Function |
|-----------|----------|
| `FallbackHandler` | Routes to baseline when local fails (timeout, error, invalid output) |
| `CircuitBreaker` | Opens after N consecutive failures, prevents cascading failure |
| `RollbackMonitor` | Background async task that evaluates local model quality metrics |

**Rollback triggers** (any one triggers full rollback to baseline):
1. Error rate > 5% (configurable)
2. p95 latency > 5000ms (configurable)
3. Accuracy < 85% (requires ≥30 labelled samples)

#### 3.3 Metrics & Observability

**In-memory** (`MetricsCollector`): Windowed (10k requests), O(1) recording, serves `/metrics`.

**Persistent** (SQLAlchemy async): Full request logs with input text, predictions,
latency, tokens, cost, route, correctness. Supports both SQLite (dev) and PostgreSQL (prod).

#### 3.4 Cost Model (`evaluation/cost.py`)

Uses configurable `PricingAssumptions` — never hardcoded values.

- **API cost**: `(input_tokens × input_price/Mtok) + (output_tokens × output_price/Mtok)`
- **Local cost**: `machine_cost_per_hour / queries_per_hour`
- **Break-even**: Monthly query volume where local becomes cheaper
- **Sensitivity**: Low/Base/High scenarios for machine cost

### 4. Data Flow

```
1. Client → POST /classify {message, user_id?, ground_truth?}
2. RoutingEngine.determine_route(user_id) → BASELINE | LOCAL | SHADOW
3. If LOCAL → FallbackHandler.predict_with_fallback(message)
   - Try local → success → return
   - Try local → fail → fallback to baseline → log fallback
4. If SHADOW → predict both, return baseline to client, log local silently
5. If BASELINE → baseline.predict(message)
6. Log to DB (async, non-blocking)
7. Update in-memory MetricsCollector
8. Return ClassifyResponse {prediction, route, latency_ms, ...}
```

### 5. Security

- Admin endpoints protected by `X-API-Key` header
- Fault injection disabled by default, gated behind `FAULT_INJECTION_ENABLED` env var
- API keys never logged (structlog redaction)
- CORS configured (restrict in production)

### 6. Deployment Modes

| Mode | Database | Local Model | Baseline |
|------|----------|-------------|----------|
| Development | SQLite | Optional | MockBaseline |
| Staging | PostgreSQL | llama.cpp Q4_K_M | OpenAI API |
| Production | PostgreSQL | llama.cpp Q4_K_M | OpenAI API |

### 7. Resource Budget (MacBook Air M4, 16GB)

| Component | Memory | Notes |
|-----------|--------|-------|
| Gateway (FastAPI) | ~150 MB | Single worker |
| llama.cpp server | ~2-3 GB | Q4_K_M, 2048 ctx |
| PostgreSQL | ~200 MB | Or SQLite for dev |
| Streamlit Dashboard | ~150 MB | Single tab |
| **Total** | **~3-4 GB** | Leaves 12+ GB for OS |
