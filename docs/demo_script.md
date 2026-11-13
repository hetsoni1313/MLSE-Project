# Demo Script — 5-Minute Demonstration

## Prerequisites
- Gateway running: `uvicorn gateway.main:app --port 8000`
- Dashboard running: `streamlit run dashboard/app.py --server.port 8501`
- Golden test data prepared: `python scripts/prepare_data.py`

---

## Minute 1 — Baseline (100% Commercial API)

```bash
# Verify baseline-only routing
curl -s http://localhost:8000/admin/config -H "X-API-Key: change-me-in-production" | python3 -m json.tool

# Run baseline traffic
python -m loadtest.replay --scenario baseline --requests 30 --concurrency 2

# Show dashboard — Executive Overview
# Point out: all traffic to baseline, accuracy, latency, cost
```

**Talking points**: All traffic routes to the commercial API. We measure accuracy, latency, and cost as our baseline reference.

---

## Minute 2 — Shadow Mode

```bash
# Enable shadow mode
curl -X PUT http://localhost:8000/admin/config \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me-in-production" \
  -d '{"routing_mode": "shadow", "shadow_enabled": true, "reason": "Demo: enable shadow"}'

# Run shadow traffic
python -m loadtest.replay --scenario shadow --requests 30 --concurrency 2

# Dashboard shows: baseline predictions returned to client
# Local model predictions logged for comparison
```

**Talking points**: The client always gets the baseline response, but the local model runs silently. We can compare without risk.

---

## Minute 3 — Canary Deployment (10% → 50%)

```bash
# Start with 10% local traffic
curl -X PUT http://localhost:8000/admin/config \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me-in-production" \
  -d '{"routing_mode": "weighted", "baseline_percentage": 90, "local_percentage": 10}'

python -m loadtest.replay --scenario canary_10 --requests 30

# Increase to 50%
curl -X PUT http://localhost:8000/admin/config \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me-in-production" \
  -d '{"routing_mode": "weighted", "baseline_percentage": 50, "local_percentage": 50}'

python -m loadtest.replay --scenario canary_50 --requests 30

# Dashboard: traffic distribution pie chart changes
# Cost Intelligence page: cost reduction with more local traffic
```

---

## Minute 4 — Failure & Automatic Protection

```bash
# Enable fault injection (simulate local server failure)
curl -X POST http://localhost:8000/admin/faults \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me-in-production" \
  -d '{"action": "enable"}'

curl -X POST http://localhost:8000/admin/faults \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me-in-production" \
  -d '{"action": "set", "fault_type": "unavailable", "enabled": true}'

# Send requests — should fallback to baseline
python -m loadtest.replay --scenario failure_test --requests 20

# Dashboard: fallback count increases, all requests still succeed

# Now test degraded accuracy → automatic rollback
curl -X POST http://localhost:8000/admin/faults \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me-in-production" \
  -d '{"action": "set", "fault_type": "unavailable", "enabled": false}'

curl -X POST http://localhost:8000/admin/faults \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me-in-production" \
  -d '{"action": "set", "fault_type": "degraded_accuracy", "enabled": true}'

python -m loadtest.replay --scenario degraded --requests 50

# Dashboard: rollback event appears, traffic shifts to 100% baseline

# Disable faults
curl -X POST http://localhost:8000/admin/faults \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me-in-production" \
  -d '{"action": "disable"}'
```

---

## Minute 5 — Economic & Quality Evidence

Open Dashboard pages:
1. **Cost Intelligence** — Cost per 1K queries comparison, break-even chart
2. **Model Performance** — Accuracy comparison, per-class analysis
3. **Latency & Throughput** — p50/p95 latency distributions
4. **Routing & Reliability** — Rollback event log, fallback timeline

```bash
# Show metrics summary
curl -s http://localhost:8000/metrics | python3 -m json.tool

# Show rollback history
curl -s http://localhost:8000/admin/rollback-history \
  -H "X-API-Key: change-me-in-production" | python3 -m json.tool
```

**Talking points**: 
- The platform automatically detected degraded performance and rolled back
- Cost comparison shows potential savings with local inference
- All events are logged and auditable
- The system maintained service quality throughout the transition

