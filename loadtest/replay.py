"""Traffic replay engine — replay golden test data through the gateway."""

from __future__ import annotations

import asyncio
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

# Add project root to path for imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from llmops_governance.logging.setup import get_logger

logger = get_logger(__name__)


SCENARIOS = {
    "baseline": {"mode": "baseline", "baseline_pct": 100, "local_pct": 0, "desc": "100% baseline traffic"},
    "shadow": {"mode": "shadow", "baseline_pct": 100, "local_pct": 0, "shadow": True, "desc": "Shadow mode — local runs silently"},
    "canary_10": {"mode": "weighted", "baseline_pct": 90, "local_pct": 10, "desc": "90/10 canary split"},
    "canary_50": {"mode": "weighted", "baseline_pct": 50, "local_pct": 50, "desc": "50/50 traffic split"},
    "full_local": {"mode": "weighted", "baseline_pct": 0, "local_pct": 100, "desc": "100% local traffic"},
    "failure_test": {"mode": "weighted", "baseline_pct": 0, "local_pct": 100, "desc": "Local failure test — stop local server", "fault": "unavailable"},
    "degraded": {"mode": "weighted", "baseline_pct": 50, "local_pct": 50, "desc": "Degraded accuracy test", "fault": "degraded_accuracy"},
}


async def set_routing_config(
    gateway_url: str,
    admin_key: str,
    config: dict,
) -> bool:
    """Update gateway routing configuration."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.put(
                f"{gateway_url}/admin/config",
                headers={"X-API-Key": admin_key},
                json={
                    "routing_mode": config.get("mode", "baseline"),
                    "baseline_percentage": config.get("baseline_pct", 100),
                    "local_percentage": config.get("local_pct", 0),
                    "shadow_enabled": config.get("shadow", False),
                    "reason": f"Load test scenario: {config.get('desc', '')}",
                },
            )
            return response.status_code == 200  # noqa: PLR2004
        except Exception as e:
            logger.error("config_update_failed", error=str(e))
            return False


async def set_fault(
    gateway_url: str,
    admin_key: str,
    fault_type: str,
    enabled: bool = True,
) -> bool:
    """Toggle fault injection."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            body: dict = {"action": "enable" if enabled else "disable"}
            if enabled:
                body = {"action": "set", "fault_type": fault_type, "enabled": True}
            response = await client.post(
                f"{gateway_url}/admin/faults",
                headers={"X-API-Key": admin_key},
                json=body,
            )
            return response.status_code == 200  # noqa: PLR2004
        except Exception:
            return False


async def replay_dataset(
    gateway_url: str,
    dataset: list[dict],
    concurrency: int = 2,
    num_requests: int | None = None,
    delay_ms: int = 100,
    experiment_id: str = "",
) -> list[dict]:
    """Replay dataset entries through the gateway."""
    semaphore = asyncio.Semaphore(concurrency)
    entries = dataset[:num_requests] if num_requests else dataset
    results: list[dict] = []

    async with httpx.AsyncClient(timeout=30) as client:

        async def send_one(idx: int, entry: dict) -> dict:
            async with semaphore:
                start = time.perf_counter()
                try:
                    resp = await client.post(
                        f"{gateway_url}/classify",
                        json={
                            "message": entry["text"],
                            "ground_truth": entry.get("label"),
                            "request_id": f"{experiment_id}-{idx}",
                            "user_id": f"user-{idx % 100}",
                        },
                    )
                    elapsed = (time.perf_counter() - start) * 1000
                    data = resp.json()
                    return {
                        "idx": idx,
                        "text": entry["text"],
                        "ground_truth": entry.get("label", ""),
                        "prediction": data.get("prediction", ""),
                        "route": data.get("route", ""),
                        "latency_ms": elapsed,
                        "fallback_used": data.get("fallback_used", False),
                        "error": data.get("error"),
                    }
                except Exception as e:
                    elapsed = (time.perf_counter() - start) * 1000
                    return {
                        "idx": idx,
                        "text": entry["text"],
                        "ground_truth": entry.get("label", ""),
                        "prediction": "",
                        "route": "error",
                        "latency_ms": elapsed,
                        "error": str(e),
                    }

        tasks = [send_one(i, entry) for i, entry in enumerate(entries)]
        results = await asyncio.gather(*tasks)

    return list(results)


async def run_scenario(
    scenario_name: str,
    gateway_url: str = "http://localhost:8000",
    admin_key: str = "change-me-in-production",
    num_requests: int = 50,
    concurrency: int = 2,
) -> dict:
    """Run a complete experiment scenario."""
    if scenario_name not in SCENARIOS:
        print(f"❌ Unknown scenario: {scenario_name}")
        print(f"   Available: {', '.join(SCENARIOS.keys())}")
        return {}

    scenario = SCENARIOS[scenario_name]
    experiment_id = f"{scenario_name}-{uuid.uuid4().hex[:8]}"

    print(f"\n{'='*60}")
    print(f"🧪 Scenario: {scenario_name}")
    print(f"   {scenario['desc']}")
    print(f"   Experiment ID: {experiment_id}")
    print(f"   Requests: {num_requests}, Concurrency: {concurrency}")
    print(f"{'='*60}\n")

    # Set routing config
    print("⚙️  Setting routing configuration...")
    await set_routing_config(gateway_url, admin_key, scenario)

    # Enable fault injection if needed
    if "fault" in scenario:
        print(f"💥 Enabling fault: {scenario['fault']}")
        # First enable fault injection
        await set_fault(gateway_url, admin_key, "", True)
        await asyncio.sleep(0.5)
        await set_fault(gateway_url, admin_key, scenario["fault"], True)

    # Load golden test set
    golden_path = _PROJECT_ROOT / "data" / "splits" / "golden_test.json"
    if not golden_path.exists():
        print("❌ Golden test set not found. Run: python scripts/prepare_data.py")
        return {}

    with open(golden_path) as f:
        dataset = json.load(f)

    # Run replay
    print(f"🚀 Sending {num_requests} requests...")
    start = time.perf_counter()
    results = await replay_dataset(
        gateway_url=gateway_url,
        dataset=dataset,
        concurrency=concurrency,
        num_requests=num_requests,
        experiment_id=experiment_id,
    )
    total_time = time.perf_counter() - start

    # Disable fault injection
    if "fault" in scenario:
        await set_fault(gateway_url, admin_key, scenario["fault"], False)

    # Calculate summary
    correct = sum(1 for r in results if r.get("prediction") == r.get("ground_truth") and r.get("ground_truth"))
    labelled = sum(1 for r in results if r.get("ground_truth"))
    errors = sum(1 for r in results if r.get("error"))
    fallbacks = sum(1 for r in results if r.get("fallback_used"))
    latencies = [r["latency_ms"] for r in results if r["latency_ms"] > 0]

    summary = {
        "experiment_id": experiment_id,
        "scenario": scenario_name,
        "total_requests": len(results),
        "total_time_s": round(total_time, 2),
        "accuracy": correct / labelled if labelled > 0 else 0.0,
        "error_count": errors,
        "fallback_count": fallbacks,
        "mean_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
        "p95_latency_ms": sorted(latencies)[min(int(len(latencies) * 0.95), len(latencies) - 1)] if latencies else 0,
        "throughput_qps": len(results) / total_time if total_time > 0 else 0,
    }

    print(f"\n📊 Results:")
    print(f"   Accuracy:    {summary['accuracy']:.1%}")
    print(f"   Errors:      {summary['error_count']}")
    print(f"   Fallbacks:   {summary['fallback_count']}")
    print(f"   Mean latency: {summary['mean_latency_ms']:.1f} ms")
    print(f"   p95 latency:  {summary['p95_latency_ms']:.1f} ms")
    print(f"   Throughput:   {summary['throughput_qps']:.1f} QPS")
    print(f"   Total time:   {summary['total_time_s']:.1f}s")

    # Save results
    results_dir = _PROJECT_ROOT / "experiments" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    output_path = results_dir / f"{experiment_id}.json"
    with open(output_path, "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)
    print(f"   Saved to: {output_path}")

    return summary


def main() -> None:
    """CLI entry point for running experiments."""
    import argparse

    parser = argparse.ArgumentParser(description="LLMOps Traffic Replay Engine")
    parser.add_argument("--scenario", default="baseline", choices=list(SCENARIOS.keys()))
    parser.add_argument("--gateway", default="http://localhost:8000")
    parser.add_argument("--admin-key", default="change-me-in-production")
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--all", action="store_true", help="Run all scenarios")
    args = parser.parse_args()

    if args.all:
        for name in SCENARIOS:
            asyncio.run(run_scenario(name, args.gateway, args.admin_key, args.requests, args.concurrency))
    else:
        asyncio.run(run_scenario(args.scenario, args.gateway, args.admin_key, args.requests, args.concurrency))


if __name__ == "__main__":
    main()

