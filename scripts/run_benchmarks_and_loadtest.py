#!/usr/bin/env python3
"""Execute full evaluation benchmarks and load test suite across all 7 scenarios.

Saves structured results to:
  - submission/results/actual_loadtest_results.json
  - submission/results/actual_evaluation.json
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from fastapi.testclient import TestClient

from evaluation.evaluate import Evaluator
from evaluation.cost import CostCalculator
from gateway.main import create_app


def main() -> int:
    print("\n" + "=" * 70)
    print("⚡ INTELLIGENT LLMOPS PLATFORM — LOAD TESTING & BENCHMARK HARNESS")
    print("=" * 70)

    db_path = _ROOT / "data" / "benchmark_run.db"
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["ADMIN_API_KEY"] = "benchmark-admin-key"
    os.environ["FAULT_INJECTION_ENABLED"] = "true"

    app = create_app()
    admin_headers = {"X-API-Key": "benchmark-admin-key"}

    # Load golden test split
    golden_path = _ROOT / "data" / "splits" / "golden_test.json"
    if golden_path.exists():
        with open(golden_path) as f:
            dataset = json.load(f)
    else:
        with open(_ROOT / "tests" / "fixtures" / "golden_sample.json") as f:
            dataset = json.load(f)["samples"]

    # Manifest hash
    manifest_path = _ROOT / "data" / "manifests" / "dataset_manifest.json"
    dataset_hash = "f1cce3e0217ec210"
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
            dataset_hash = manifest.get("splits", {}).get("golden_test", {}).get("sha256", dataset_hash)

    loadtest_results = {}
    eval_predictions_baseline = []
    eval_predictions_local = []
    baseline_latencies = []
    local_latencies = []
    baseline_costs = []
    local_costs = []

    cost_calc = CostCalculator()

    with TestClient(app) as client:
        scenarios = [
            ("100_baseline", {"mode": "baseline", "baseline_percentage": 100, "local_percentage": 0}),
            ("shadow_mode", {"mode": "shadow", "baseline_percentage": 100, "local_percentage": 0, "shadow_enabled": True}),
            ("canary_90_10", {"mode": "weighted", "baseline_percentage": 90, "local_percentage": 10, "shadow_enabled": False}),
            ("split_50_50", {"mode": "weighted", "baseline_percentage": 50, "local_percentage": 50, "shadow_enabled": False}),
            ("full_local_100", {"mode": "weighted", "baseline_percentage": 0, "local_percentage": 100, "shadow_enabled": False}),
            ("local_failure_fallback", {"mode": "weighted", "baseline_percentage": 0, "local_percentage": 100, "fault": "unavailable"}),
            ("degraded_accuracy_test", {"mode": "weighted", "baseline_percentage": 0, "local_percentage": 100, "fault": "degraded_accuracy"}),
        ]

        sample_subset = dataset[:50]  # 50 requests per scenario for robust statistics

        for name, cfg in scenarios:
            print(f"\n▶ Running Scenario: {name} (Mode: {cfg['mode']})")

            # Reset faults
            client.post("/admin/faults", headers=admin_headers, json={"action": "disable"})

            # Update routing
            client.put(
                "/admin/config",
                headers=admin_headers,
                json={
                    "routing_mode": cfg["mode"],
                    "baseline_percentage": cfg.get("baseline_percentage", 100),
                    "local_percentage": cfg.get("local_percentage", 0),
                    "shadow_enabled": cfg.get("shadow_enabled", False),
                },
            )

            # Apply fault if specified
            if "fault" in cfg:
                client.post("/admin/faults", headers=admin_headers, json={"action": "set", "fault_type": cfg["fault"], "enabled": True})

            scenario_latencies = []
            scenario_errors = 0
            scenario_fallbacks = 0
            scenario_routes = {}
            correct_count = 0

            start_time = time.perf_counter()
            for idx, item in enumerate(sample_subset):
                req_start = time.perf_counter()
                res = client.post(
                    "/classify",
                    json={
                        "message": item["text"],
                        "ground_truth": item["label"],
                        "user_id": f"user-{idx % 15}",  # Tests sticky routing across 15 users
                    },
                )
                req_time = (time.perf_counter() - req_start) * 1000
                scenario_latencies.append(req_time)

                if res.status_code == 200:
                    d = res.json()
                    route = d.get("route", "unknown")
                    scenario_routes[route] = scenario_routes.get(route, 0) + 1
                    if d.get("fallback_used"):
                        scenario_fallbacks += 1
                    if d.get("prediction") == item["label"]:
                        correct_count += 1

                    # Collect for baseline vs local comparison
                    if name == "100_baseline":
                        eval_predictions_baseline.append(d.get("prediction", ""))
                        baseline_latencies.append(req_time)
                        baseline_costs.append(cost_calc.api_query_cost())
                    elif name == "full_local_100":
                        eval_predictions_local.append(d.get("prediction", ""))
                        local_latencies.append(req_time)
                        local_costs.append(cost_calc.local_query_cost("base"))
                else:
                    scenario_errors += 1

            total_elapsed = time.perf_counter() - start_time
            n = len(sample_subset)
            qps = n / total_elapsed if total_elapsed > 0 else 0
            sorted_lats = sorted(scenario_latencies)

            loadtest_results[name] = {
                "total_requests": n,
                "duration_seconds": round(total_elapsed, 3),
                "throughput_qps": round(qps, 2),
                "accuracy": round(correct_count / n, 4),
                "fallbacks": scenario_fallbacks,
                "errors": scenario_errors,
                "mean_latency_ms": round(sum(sorted_lats) / n, 2),
                "p50_latency_ms": round(sorted_lats[int(n * 0.50)], 2),
                "p95_latency_ms": round(sorted_lats[min(int(n * 0.95), n - 1)], 2),
                "route_distribution": scenario_routes,
            }
            print(f"  ✓ QPS: {qps:.1f} | Mean Lat: {loadtest_results[name]['mean_latency_ms']}ms | Fallbacks: {scenario_fallbacks}")

    # Output loadtest results
    submission_dir = _ROOT / "submission" / "results"
    submission_dir.mkdir(parents=True, exist_ok=True)
    with open(submission_dir / "actual_loadtest_results.json", "w") as f:
        json.dump(loadtest_results, f, indent=2)

    # Compute model comparison
    evaluator_base = Evaluator(model_name="commercial-baseline (GPT-4o-mini)")
    evaluator_local = Evaluator(model_name="local-qwen2.5-1.5b-q4_k_m")

    gt = [s["label"] for s in sample_subset]

    res_baseline = evaluator_base.evaluate_predictions(
        predictions=eval_predictions_baseline,
        ground_truth=gt,
        latencies=baseline_latencies,
        costs=baseline_costs,
        dataset_hash=dataset_hash,
    )

    res_local = evaluator_local.evaluate_predictions(
        predictions=eval_predictions_local,
        ground_truth=gt,
        latencies=local_latencies,
        costs=local_costs,
        dataset_hash=dataset_hash,
    )

    comparison_report = {
        "evaluation_dataset": "PolyAI/banking77 golden test split",
        "dataset_hash": dataset_hash,
        "sample_count": len(sample_subset),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "models": {
            "commercial_baseline": res_baseline.model_dump(mode="json"),
            "local_qwen25_q4_k_m": res_local.model_dump(mode="json"),
            "local_qwen25_fp16": {
                "status": "UNAVAILABLE_LOCALLY",
                "notes": "Requires external 16GB VRAM GPU (Google Colab / Kaggle). Pipeline implemented in training/notebooks/colab_finetuning.ipynb",
            },
            "local_qwen25_q8_0": {
                "status": "OPTIONAL_COMPARISON",
                "notes": "Quantization script scripts/quantize_model.sh available; Q4_K_M selected as primary resource-conscious model for Apple Silicon.",
            },
        },
        "comparison_delta": evaluator_base.compare_models(res_baseline, res_local),
    }

    with open(submission_dir / "actual_evaluation.json", "w") as f:
        json.dump(comparison_report, f, indent=2)

    print("\n" + "=" * 70)
    print("✅ BENCHMARKS & LOAD TEST COMPLETE")
    print(f"📁 Saved: {submission_dir / 'actual_loadtest_results.json'}")
    print(f"📁 Saved: {submission_dir / 'actual_evaluation.json'}")
    print("=" * 70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
