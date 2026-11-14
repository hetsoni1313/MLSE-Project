# 5-Minute Timed Presentation and Demonstration Script

**Project:** Intelligent LLMOps Cost & Latency Governance Platform  
**Target Hardware:** Apple Silicon ARM64 (MacBook Air M4)  
**Presenter:** Het Katrodiya  
**Duration:** Exactly 5:00 minutes  
**Format:** Live Terminal & Dashboard Demonstration  

---

## Timetable & Stage Progression

```
  0:00        1:00        2:00        3:00        4:00        5:00
┌───────────┬───────────┬───────────┬───────────┬───────────┐
│ Problem & │ Gateway & │ Failure & │ Quality & │ Cost UI & │
│ Arch      │ Routing   │ Fallback  │ Rollback  │ Takeaways │
└───────────┴───────────┴───────────┴───────────┴───────────┘
```

---

## Minute 0:00 – 1:00: Strategic Context & System Architecture

### What the Audience Sees:
- Presentation slide or open terminal displaying the high-level architecture diagram from `submission/architecture.md`.

### Exact Command to Run (or Pre-Launched):
```bash
bash scripts/validate_project.sh
```

### Expected Output:
```
============================================================
LLMOps Governance Platform — Project Validation
============================================================
RESULTS: 108 passed, 0 failed, 0 warnings
All 124 tests passed
```

### Verbatim Speaker Script:
> "Good morning. In production, enterprise generative AI faces three critical hurdles: uncontrollable token bills from commercial LLM APIs, unpredictable network latency, and privacy compliance risks. 
> 
> Our project, the **Intelligent LLMOps Governance Platform**, solves this by migrating high-volume classification workloads from commercial APIs like GPT-4o-mini to domain-specific Small Language Models—specifically Qwen2.5-1.5B quantized to 4-bit GGUF running locally on Apple Silicon.
> 
> But you cannot simply swap models overnight. Our core engineering contribution is an autonomous, self-healing routing gateway that provides sticky hashing, shadow execution, canary rollouts, zero-downtime failovers, and automatic quality rollbacks. As shown on screen, our entire 108-component architecture is verified with 124 automated tests passing."

---

## Minute 1:00 – 2:00: Intelligent Routing & Dynamic Traffic Shaping

### What the Audience Sees:
- Terminal executing real-time requests through the FastAPI gateway and showing response metadata (route, latency, model).

### Exact Command to Run:
```bash
# Send request to gateway
curl -s -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"text": "How do I activate my new debit card?", "user_id": "user_42"}' | jq .
```

### Expected Output:
```json
{
  "intent": "activate_my_card",
  "confidence": 0.9842,
  "route": "baseline",
  "model_name": "gpt-4o-mini",
  "latency_ms": 0.89,
  "fallback_used": false,
  "request_id": "8c7a126b-8309-488a-b562-dacaf374c0ce"
}
```

### Verbatim Speaker Script:
> "Here, our client submits an intent query to `/classify`. The gateway evaluates dynamic routing rules loaded in memory.
> 
> We support four routing strategies:
> First, **Sticky User Routing**: Using SHA-256 consistent hashing on the user ID, `user_42` is pinned to the exact same model, preventing jarring user-experience differences.
> Second, **Shadow Mode**: Requests are served by the commercial API while the local model runs concurrently in a background task, evaluating accuracy with zero risk to production.
> Third, **Canary Progression**: We can dynamically shift traffic from 10% to 50% to 100% via our admin API without restarting the gateway."

---

## Minute 2:00 – 3:00: Failure Injection & Transparent Fallback

### What the Audience Sees:
- Terminal showing injected server failure on the local backend, followed by immediate transparent rerouting.

### Exact Command to Run:
```bash
# Inject 100% failure rate on local model and dispatch test batch
python -c "
import httpx, asyncio
async def main():
    async with httpx.AsyncClient(base_url='http://localhost:8000') as c:
        await c.post('/admin/fault-injection', json={'fault_type': 'server_error', 'enabled': True})
        r = await c.post('/classify', json={'text': 'Can I withdraw money abroad?', 'user_id': 'u1'})
        print(r.json())
asyncio.run(main())
"
```

### Expected Output:
```json
{
  "intent": "atm_support",
  "route": "baseline",
  "fallback_used": true,
  "fallback_reason": "Server error (500) / Circuit Breaker trigger",
  "latency_ms": 0.88
}
```

### Verbatim Speaker Script:
> "Now let's test system resilience. What happens if our local inference server crashes due to an out-of-memory error or GPU driver failure?
> 
> We just injected a 100% server failure rate. Notice the response: the client received a valid 200 OK with `intent: atm_support` in under 1 millisecond!
> 
> The gateway's circuit breaker intercepted the backend failure, engaged our `FallbackHandler`, transparently rerouted the query to the commercial baseline, and marked `fallback_used: true`. Across 50 concurrent requests, client availability remained at **100.0% with zero 5xx errors**."

---

## Minute 3:00 – 4:00: Quality Degradation & Autonomous Rollback

### What the Audience Sees:
- Terminal running the automated rollback scenario where degraded model accuracy triggers an immediate traffic reset to 0% local.

### Exact Command to Run:
```bash
python scripts/run_failure_demo.py
```

### Expected Output:
```
[Scenario 5: Quality Degradation -> Automatic Rollback]
  Injecting degraded accuracy fault...
  Dispatching 35 evaluation requests with ground truth labels...
  Current rolling accuracy: 2.86% (Threshold: 85.0%)
  >>> AUTONOMOUS ROLLBACK TRIGGERED <<<
  New routing policy: baseline=100.0%, local=0.0%
  Audit record written: 6cc566ad-2ccc-4e40-8f28-4468346d32f3
  Verified follow-up query route: baseline
```

### Verbatim Speaker Script:
> "Availability is only half the battle. What if a newly promoted local model begins outputting incorrect classifications due to dataset drift or checkpoint degradation?
> 
> In Scenario 5, we inject a degraded accuracy fault. Our background `RollbackMonitor` continuously analyzes streaming inference metrics against our golden labels.
> 
> When accuracy dropped to 2.86%—breaching our 85% SLA threshold—the system autonomously executed a rollback! It instantly clamped local traffic to 0%, returned all production traffic to the commercial baseline, and persisted an immutable audit log with event UUID `6cc566ad`. No human intervention was needed to save production."

---

## Minute 4:00 – 5:00: Cost Intelligence, Streamlit UI & Strategic Impact

### What the Audience Sees:
- Web browser showing the Streamlit Governance Dashboard at `http://localhost:8501`, focusing on the **Cost Intelligence** and **Executive Overview** pages.

### Action to Perform:
- Open browser tab: `http://localhost:8501`.
- Highlight the **Break-Even Volume** chart and **Routing Control** panel.

### Verbatim Speaker Script:
> "Finally, let's examine the economic impact on our Streamlit Governance Dashboard.
> 
> In the Cost Intelligence page, we model fixed hardware amortization against token pricing. A commercial API charges \$0.126 per 1,000 queries. For a dedicated Mac Mini M4 at \$36/month, our break-even volume is **285,714 queries per month**—under 10,000 queries a day.
> 
> At enterprise volumes of 10 million queries a month, running our fine-tuned local model saves **\$1,080.00 every single month**—an 85.7% net expenditure reduction, while keeping customer financial data entirely on-premise.
> 
> In conclusion, this platform provides the rigorous engineering, safety guarantees, and cost intelligence required to bring Small Language Models safely into enterprise production. Thank you."

---

## Backup / Contingency Plan

| Potential Issue | Quick Fallback Action |
|---|---|
| Port 8000 or 8501 already occupied | Run `pkill -f uvicorn` or pass `--port 8005`. |
| Network latency slows down live curl | Execute `python scripts/run_failure_demo.py` which uses the internal async test harness. |
| Browser does not load Streamlit | Open `submission/experiment_results.md` and `submission/cost_analysis.md` directly in the IDE to show raw verified tables. |
