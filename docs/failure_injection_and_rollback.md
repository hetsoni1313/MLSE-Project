# Failure Injection, Fallback, and Automatic Rollback Architecture

## 1. Overview and Operational Philosophy

In production LLMOps environments, serving fine-tuned smaller models (SLMs) locally offers substantial cost and data-privacy benefits. However, local inference models are susceptible to:
1. **Infrastructure Failures**: Out-of-memory (OOM) errors, GPU/NPU driver stalls, HTTP connection drops to llama.cpp / vLLM servers.
2. **Quality Degradation**: Sub-optimal fine-tuning checkpoints, catastrophic forgetting, distribution drift leading to invalid or incorrect classification.
3. **Latency Spikes**: Context saturation, thread contention, or throttling resulting in SLA breaches (>5000ms).

The **LLMOps Cost & Latency Governance Platform** implements an industrial-grade, multi-tier resilience architecture:

```
                    ┌─────────────────────────────────────────────────┐
                    │            Client Request / Load Test           │
                    └────────────────────────┬────────────────────────┘
                                             │
                                     POST /classify
                                             │
                                             ▼
                    ┌─────────────────────────────────────────────────┐
                    │               FastAPI Gateway                   │
                    │                                                 │
                    │  ┌───────────────────────────────────────────┐  │
                    │  │              Routing Engine               │  │
                    │  │ (Weighted / Sticky / Shadow / Canary)     │  │
                    │  └─────────────────────┬─────────────────────┘  │
                    │                        │                        │
                    │                        ▼                        │
                    │  ┌───────────────────────────────────────────┐  │
                    │  │             Resilience Layer              │  │
                    │  │                                           │  │
                    │  │  ┌─────────────────────────────────────┐  │  │
                    │  │  │        Circuit Breaker              │  │  │
                    │  │  │  (CLOSED -> OPEN -> HALF_OPEN)      │  │  │
                    │  │  └──────────────────┬──────────────────┘  │  │
                    │  │                     │                     │  │
                    │  │  ┌──────────────────▼──────────────────┐  │  │
                    │  │  │         Fallback Handler            │  │  │
                    │  │  │ (Transparent rerouting to Baseline) │  │  │
                    │  │  └──────────────────┬──────────────────┘  │  │
                    │  │                     │                     │  │
                    │  │  ┌──────────────────▼──────────────────┐  │  │
                    │  │  │         Rollback Monitor            │  │  │
                    │  │  │ (Background Evaluator: Acc/Err/p95) │  │  │
                    │  │  └─────────────────────────────────────┘  │  │
                    │  └───────────────────────────────────────────┘  │
                    └────────────────────────┬────────────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       │                                           │
                       ▼                                           ▼
         ┌───────────────────────────┐               ┌───────────────────────────┐
         │     Commercial API        │               │    Local Fine-Tuned       │
         │   (GPT-4o-mini Baseline)  │               │      (Qwen2.5 GGUF)       │
         └─────────────┬─────────────┘               └─────────────┬─────────────┘
                       │                                           │
                       └─────────────────────┬─────────────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │   PostgreSQL / SQLite     │
                               │    (Audit & Metrics)      │
                               └───────────────────────────┘
```

---

## 2. Injected Failure Modes

The platform includes a dedicated `FaultInjectionBackend` ([gateway/backends/fault_injection.py](file:///Users/hetkatrodiya/Desktop/SEM-3/Machine%20Learning%20System%20Engneering/Project/MLSE-Project/gateway/backends/fault_injection.py)) that wraps the local inference engine and supports 6 distinct failure mechanisms:

| Failure Mode | Trigger Mechanism | Expected System Response | Client Impact |
|---|---|---|---|
| **1. Server Unavailable** | Injected HTTP 503 / connection drop | `FallbackHandler` intercepts failure, routes to Commercial Baseline API | **Zero 5xx errors**, HTTP 200 OK returned |
| **2. Request Timeout** | Sleep delay exceeding `local_model_timeout_ms` (10s) | Circuit breaker increments failure count, `FallbackHandler` redirects to Baseline | HTTP 200 OK returned with `fallback_used: true` |
| **3. Random Error Rate** | Configurable % of requests fail with `[FAULT INJECTION] Random error` | `RollbackMonitor` detects error rate > 5%, triggers automatic rollback | Traffic shifts to 100% baseline |
| **4. High Latency** | Artificial latency injection (> 5,000ms) | `RollbackMonitor` detects $p95 > 5000\text{ ms}$, triggers automatic rollback | Traffic shifts to 100% baseline |
| **5. Invalid Outputs** | Injected prediction `"INVALID_INJECTED_LABEL"` | `validate_label()` fails, `FallbackHandler` reroutes to Baseline | Correct baseline intent returned |
| **6. Degraded Accuracy** | Systematically replaces correct label with wrong Banking77 intent | `RollbackMonitor` detects accuracy < 85% on $\ge 30$ labelled samples, triggers rollback | Local traffic reduced to 0% |

---

## 3. Threshold Configuration and Safety Rules

Configured in `configs/thresholds.yaml` and instantiated via `RollbackSettings` ([src/llmops_governance/config/settings.py](file:///Users/hetkatrodiya/Desktop/SEM-3/Machine%20Learning%20System%20Engneering/Project/MLSE-Project/src/llmops_governance/config/settings.py)):

```yaml
rollback:
  enabled: true
  evaluation_window: 100         # Rolling evaluation window of recent requests
  min_labelled_samples: 30       # Safety barrier: never rollback accuracy without statistical mass
  min_accuracy: 0.85             # Minimum acceptable classification accuracy (85%)
  max_error_rate: 0.05           # Maximum allowable error rate (5%)
  max_p95_latency_ms: 5000.0     # Maximum allowable p95 response time (5,000ms)
  check_interval_seconds: 30     # Background evaluation cycle frequency
  local_percentage_on_rollback: 0 # Target local percentage when rollback triggers
```

### Safety Rules
1. **Statistical Significance Guardrail**: Accuracy-based rollback **never** executes if labelled samples in the window are fewer than `min_labelled_samples` (30). This prevents premature rollbacks on low sample sizes.
2. **Duplicate Prevention**: If the routing engine is already rolled back (`is_rolled_back = True`), subsequent threshold breaches are ignored to prevent re-entrant loops.
3. **Immutable Audit Trail**: Every rollback generates a unique UUID `event_id`, timestamps, trigger metric value, threshold value, previous and new routing percentages, and writes to the `rollback_events` table.
4. **Controlled Recovery**: Once triggered, rollback state **cannot** be automatically undone by transient lucky samples. Recovery requires an explicit authenticated administrative request to `POST /admin/reset-rollback`.

---

## 4. Execution Commands

### Run Automated Demonstration
```bash
# Execute the full end-to-end 6-scenario demonstration
./scripts/run_failure_demo.sh
```

### Manual API Control
```bash
# 1. Update routing to 50/50 Canary
curl -X PUT http://localhost:8000/admin/config \
  -H "X-API-Key: change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"routing_mode": "weighted", "baseline_percentage": 50, "local_percentage": 50}'

# 2. Inject Server Unavailable Fault
curl -X POST http://localhost:8000/admin/faults \
  -H "X-API-Key: change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"action": "set", "fault_type": "unavailable", "enabled": true}'

# 3. Trigger Immediate Rollback Check
curl -X POST http://localhost:8000/admin/check-rollback \
  -H "X-API-Key: change-me-in-production"

# 4. View Rollback Audit Log
curl -X GET http://localhost:8000/admin/rollback-history \
  -H "X-API-Key: change-me-in-production"

# 5. Reset Rollback & Recover Traffic
curl -X POST http://localhost:8000/admin/reset-rollback \
  -H "X-API-Key: change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"routing_mode": "weighted", "baseline_percentage": 90, "local_percentage": 10}'
```

---

## 5. Actual Observed Test Evidence

The following data was captured during the execution of `./scripts/run_failure_demo.sh` on Apple Silicon macOS:

### Scenario 4: Local Server Down -> Immediate Fallback
- **Local Model State**: Injected unavailable fault.
- **Requests Sent**: 5 requests intended for the local model.
- **Observed Route**: `baseline` (100% of requests).
- **Fallback Triggered**: 5 / 5 requests ($100\%$).
- **Client Status Code**: HTTP 200 OK.
- **Client-Observed Availability**: **100.0%** (zero failed requests).

### Scenario 5: Accuracy Degradation -> Automatic Rollback
- **Degraded Accuracy Injection**: Rate = 100% wrong intent labels.
- **Sample Volume**: 35 labelled Banking77 golden samples submitted.
- **Measured Local Accuracy**: **2.86%** ($\frac{1}{35}$).
- **Threshold**: 85.0%.
- **Action Taken**: `RollbackMonitor` triggered automatic rollback.
- **Routing Configuration**:
  - `previous_local_pct`: 100%
  - `new_local_pct`: 0%
  - `new_baseline_pct`: 100%
  - `rolled_back`: `true`
- **Database Audit Record**:
  - `event_id`: `6cc566ad-2ccc-4e40-8f28-4468346d32f3`
  - `trigger_type`: `accuracy`
  - `metric_value`: `0.02857`
  - `threshold_value`: `0.85`

### Scenario 6: Administrative Recovery
- **Action**: `POST /admin/reset-rollback` with `local_percentage: 10%`.
- **Result**: `rolled_back` cleared to `false`. Local routing successfully restored to 10% canary traffic.

---

## 6. Known Limitations and Production Hardening

1. **In-Flight Requests during Failure**: If a local request times out, client-perceived latency equals `local_model_timeout_ms` (10s) + baseline latency. The `CircuitBreaker` mitigates this by tripping after 5 consecutive failures, avoiding repeated 10s timeouts.
2. **Ground-Truth Lag**: Accuracy rollback requires labelled customer feedback. For high-volume unlabelled traffic, error rate and p95 latency rollbacks provide instantaneous protection.
3. **Database Concurrency**: The request logger uses an async, non-blocking queue (`asyncio.Queue`) with batch worker writes, ensuring DB logging never adds latency to client classification responses.
