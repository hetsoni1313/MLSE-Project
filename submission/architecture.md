# System Architecture & Technical Specifications

**Project:** Intelligent LLMOps Cost & Latency Governance Platform  
**Target Hardware:** MacBook Air M4 (Apple Silicon ARM64, 16 GB Unified Memory) & Cloud GPU  
**Frameworks:** FastAPI, PyTorch / PEFT / Unsloth, llama.cpp, PostgreSQL, SQLAlchemy 2.0 Async, Streamlit, Pydantic v2  

---

## 1. High-Level Architectural Topology

The Intelligent LLMOps Platform decouples client-facing inference from upstream model execution. The platform sits as an inline reverse proxy and governance layer that evaluates, routes, protects, and logs all inference requests.

```
+---------------------------------------------------------------------------------------+
|                                CLIENT & TRAFFIC LAYER                                 |
|                                                                                       |
|   +--------------------------+                         +--------------------------+   |
|   |   Replay Simulator       |                         |  Production Applications |   |
|   |   (loadtest/replay.py)   |                         |  (REST API Clients)      |   |
|   +-------------+------------+                         +------------+-------------+   |
+-----------------|---------------------------------------------------|-----------------+
                  |                                                   |
                  +-------------------------+-------------------------+
                                            |
                                 POST /classify (JSON)
                                            |
+-------------------------------------------v-------------------------------------------+
|                              FASTAPI INLINE GATEWAY                                   |
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  | Lifespan Management: Engine Init | Circuit Breakers | Rollback Monitors         |  |
|  +----------------------------------------+----------------------------------------+  |
|                                           |                                           |
|  +----------------------------------------v----------------------------------------+  |
|  | Request Validation Middleware (Pydantic v2: ClassificationRequest)              |  |
|  +----------------------------------------+----------------------------------------+  |
|                                           |                                           |
|  +----------------------------------------v----------------------------------------+  |
|  | Intelligent Routing Engine (gateway/routing/engine.py)                          |  |
|  |  * Static/Weighted Split (0% - 100% via atomic config)                         |  |
|  |  * Sticky Consistent Hashing: SHA-256(user_id) % 100                           |  |
|  |  * Canary Phased Deployment: 5% -> 25% -> 50% -> 100%                            |  |
|  |  * Shadow Mode: Sync baseline response + async local fire-and-forget            |  |
|  +-------------------+----------------------------------------+--------------------+  |
|                      |                                        |                       |
|           Route: "baseline"                               Route: "local"              |
|                      |                                        |                       |
|                      |              +-------------------------v--------------------+  |
|                      |              | Local Circuit Breaker (3 states)             |  |
|                      |              | - Max Failures: 3 | Reset Timeout: 30s       |  |
|                      |              +-------------------------+--------------------+  |
|                      |                                        |                       |
|                      |                             Local Backend Call                 |
|                      |                             (OpenAI-Compatible / llama.cpp)    |
|                      |                                        |                       |
|                      |                      +-----------------+-----------------+     |
|                      |                      | Success?                          |     |
|                      |                      | YES           NO / Timeout (>5s)  |     |
|                      |                      |               Circuit Breaker OPEN|     |
|                      |                      |                         |         |     |
|                      |                      |                         v         |     |
|                      |                      |              Transparent Fallback |     |
|                      |                      |              (reroute to baseline)|     |
|                      |                      |                         |         |     |
|                      |                      v                         v         |     |
|                      +--------------------->+<------------------------+         |     |
|                                             |                                   |     |
|                                             v                                   |     |
|  +---------------------------------------------------------------------------------+  |
|  | Non-Blocking Request Logger (asyncio.Queue -> Batch DB Worker)                  |  |
|  +---------------------------------------------------------------------------------+  |
+---------------------------------------------|-----------------------------------------+
                                              |
                       +----------------------+----------------------+
                       |                                             |
                       v                                             v
+---------------------------------------------+ +---------------------------------------+
|          COMMERCIAL LLM BACKEND             | |         LOCAL INFERENCE BACKEND       |
|                                             | |                                       |
|  * OpenAI / Anthropic Provider API          | |  * llama.cpp Server (port 8081)       |
|  * Few-Shot Prompt Formulation              | |  * Qwen2.5-1.5B-Instruct-Q4_K_M       |
|  * Model: gpt-4o-mini                       | |  * Metal Hardware Acceleration (macOS)|
|  * Latency: ~800-1200 ms                    | |  * Latency: ~30-60 ms                 |
+---------------------------------------------+ +---------------------------------------+
                       |                                             |
                       +----------------------+----------------------+
                                              |
                                              v
+---------------------------------------------------------------------------------------+
|                               PERSISTENCE & OBSERVABILITY                             |
|                                                                                       |
|   PostgreSQL 16 (Relational Database via SQLAlchemy 2.0 Async):                       |
|   1. request_logs: Individual request traces, latency, tokens, cost, route, errors.   |
|   2. experiments: Metadata, git commit, hyperparameters, dataset hash.                |
|   3. experiment_metrics: Granular evaluation runs, accuracy, F1, latency percentiles. |
|   4. rollback_events: Immutable audit log of automated governance interventions.       |
|   5. routing_configs: Dynamic routing rules, versioning, weights, canary flags.       |
|   6. model_evaluations: Golden-set ground truth validation results.                   |
+---------------------------------------------+-----------------------------------------+
                                              |
                       +----------------------+----------------------+
                       |                                             |
                       v                                             v
+---------------------------------------------+ +---------------------------------------+
|          STREAMLIT DASHBOARD                | |           EVALUATION HARNESS          |
|                                             | |                                       |
|  * Executive Overview & Cost Savings        | |  * Golden Test Split (500 samples)    |
|  * Real-Time Latency & Throughput (p50/p95) | |  * Per-Class Precision, Recall, F1   |
|  * Traffic & Fallback Distribution          | |  * Statistical Significance Testing   |
|  * Administrative Control (Rollback Reset)  | |  * Break-Even Amortization Calculator |
+---------------------------------------------+ +---------------------------------------+
```

---

## 2. Core Subsystems and Design Decisions

### 2.1 FastAPI Gateway Core (`gateway/`)
- **Framework Choice:** FastAPI was chosen for native asynchronous coroutines (`async`/`await`), high concurrency on Apple Silicon ARM64, and automated OpenAPI 3.1 documentation.
- **Lifespan Management:** Startup initializes connection pools for PostgreSQL via asyncpg, loads routing configurations from `configs/routing.yaml`, configures the three-state circuit breaker, and launches the non-blocking background `RequestLogger` queue. Shutdown gracefully flushes remaining queue items and closes HTTP connection pools.
- **Middleware:** `RequestLoggingMiddleware` stamps every incoming request with a unique UUID4 `request_id`, tracks nanosecond-resolution monotonic execution timing, and guarantees that downstream exceptions do not escape unhandled to the client.

### 2.2 Intelligent Traffic Routing Engine (`gateway/routing/engine.py`)
The platform supports four distinct routing modalities that can be switched dynamically via the REST Admin API without restarting the application:

1. **Weighted Split:** Probabilistic routing between `baseline` (commercial API) and `local` (fine-tuned SLM) using cryptographically secure random uniform sampling:
   $$R \sim U(0, 100); \quad \text{Route} = \begin{cases} \text{local}, & \text{if } R < W_{\text{local}} \\ \text{baseline}, & \text{otherwise} \end{cases}$$
2. **Sticky User Routing:** Consistent hashing ensuring that repeat queries from the same `user_id` consistently hit the exact same backend model, eliminating user-facing behavioral drift during A/B evaluation:
   $$H = \text{SHA-256}(\text{user\_id} \mathbin{\Vert} \text{salt}) \pmod{100}$$
   $$\text{Route} = \begin{cases} \text{local}, & \text{if } H < W_{\text{local}} \\ \text{baseline}, & \text{otherwise} \end{cases}$$
3. **Shadow Mode:** The gateway routes the user request synchronously to the commercial baseline and immediately returns the response to the client. Concurrently, an `asyncio.create_task` fires the identical request to the local model in the background, logging its output, accuracy, and latency for risk-free production validation.
4. **Canary Phased Rollout:** An automated progression stage (e.g., 5% $\to$ 25% $\to$ 50% $\to$ 100%) governed by verification gates. If error rates or latency spike during any stage, traffic is automatically diverted.

### 2.3 Resilience and Governance Layer (`gateway/resilience/`)
- **Three-State Circuit Breaker (`circuit_breaker.py`):**
  - **CLOSED:** Normal operation. All routed requests execute against the target backend. Failures increment an internal counter.
  - **OPEN:** Triggered when consecutive failures $\ge 3$. All traffic destined for the local backend is immediately short-circuited and transparently diverted to the fallback baseline. No network calls are dispatched to the dead backend.
  - **HALF-OPEN:** After a configurable cooldown recovery window ($T_{\text{reset}} = 30\,\text{seconds}$), a single probe request is permitted through. If successful, the circuit resets to **CLOSED**; if it fails, it returns to **OPEN**.
- **Transparent Fallback Handler (`fallback.py`):** Wraps all local model invocations. If a network timeout ($>5.0\,\text{s}$), connection drop, invalid JSON response, or HTTP 5xx occurs, the handler intercepts the exception, records `fallback_used = True`, sets `fallback_reason`, dispatches the request to the commercial baseline, and returns a valid 200 OK classification to the caller.
- **Statistical Rollback Monitor (`rollback.py`):** Continuously monitors streaming production metrics over a rolling window ($N \ge 30$ samples). If any of the following SLA thresholds are breached:
  - $\text{Rolling Accuracy} < 85.0\%$
  - $\text{Error Rate} > 5.0\%$
  - $p_{95} \text{ Latency} > 2,000\,\text{ms}$
  
  The monitor triggers an **automatic rollback**: atomically setting $W_{\text{local}} = 0\%$ and $W_{\text{baseline}} = 100\%$, recording an immutable audit entry in `rollback_events`, and alerting administrators.

### 2.4 Asynchronous Database Persistence (`src/llmops_governance/metrics/`)
- **Database Engine:** PostgreSQL 16 managed via SQLAlchemy 2.0 with the async `asyncpg` driver.
- **Asynchronous Queueing:** To prevent database write latency from impacting client request throughput, logging is implemented as an in-memory `asyncio.Queue` coupled with a background worker task (`RequestLogger`). Worker flushes batch inserts periodically or upon reaching a batch size threshold ($B = 50$).
- **Schema Optimization:** B-Tree indices are placed on `(created_at, route)`, `user_id`, and `model_name` for sub-millisecond dashboard queries over millions of historical records.

---

## 3. Data Contracts and Interface Schemas

### 3.1 Inference Request & Response (`schemas/requests.py`)

#### Incoming `POST /classify`:
```json
{
  "text": "How do I activate my new debit card that arrived in the mail?",
  "user_id": "usr_948201a",
  "request_metadata": {
    "channel": "mobile_app",
    "region": "us-east-1"
  }
}
```

#### Outgoing `200 OK`:
```json
{
  "intent": "activate_my_card",
  "confidence": 0.9842,
  "route": "local",
  "model_name": "qwen2.5-1.5b-q4_k_m",
  "latency_ms": 34.2,
  "fallback_used": false,
  "fallback_reason": null,
  "request_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "tokens": {
    "prompt_tokens": 28,
    "completion_tokens": 6,
    "total_tokens": 34
  },
  "cost_estimate_usd": 0.0000042
}
```

---

## 4. Hardware Optimization for Apple Silicon ARM64

To ensure production-grade performance on developer workstations (MacBook Air M4, 16 GB unified memory), the following system-level optimizations were implemented:
1. **Metal GPU Acceleration:** Local inference uses `llama.cpp` compiled with Apple Metal Shading Language (`GGML_METAL=1`), executing tensor operations directly on Apple Silicon GPU cores with zero host-device memory copying.
2. **Q4_K_M Quantization:** Model weights are quantized to 4-bit medium format, compressing the Qwen2.5-1.5B model from 3.1 GB (FP16) down to 986 MB, fitting comfortably within RAM while leaving over 12 GB for the OS and services.
3. **ARM64 Native Binaries:** All Python wheels and C extensions are compiled natively for `darwin-arm64` without Rosetta 2 translation overhead.
