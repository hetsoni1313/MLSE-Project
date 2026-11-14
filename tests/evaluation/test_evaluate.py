"""Tests for evaluation orchestration and model comparison."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from evaluation.comparison import ModelComparison
from evaluation.evaluate import Evaluator
from evaluation.predictions import PredictionRunner
from gateway.backends import ModelBackend, PredictionResult
from llmops_governance.schemas.metrics import EvaluationResult


class TestEvaluator:
    """Test the Evaluator class."""

    def test_evaluate_predictions_perfect(self):
        evaluator = Evaluator(model_name="test-model")
        predictions = ["change_pin", "lost_or_stolen_card"]
        ground_truth = ["change_pin", "lost_or_stolen_card"]
        latencies = [40.0, 50.0]
        costs = [0.0001, 0.0001]

        result = evaluator.evaluate_predictions(
            predictions=predictions,
            ground_truth=ground_truth,
            latencies=latencies,
            costs=costs,
        )

        assert result.accuracy == 1.0
        assert result.macro_f1 == 1.0
        assert result.invalid_rate == 0.0
        assert result.mean_latency_ms == 45.0
        assert result.cost_per_query == 0.0001
        assert result.cost_per_1k_queries == 0.1
        assert result.total_requests == 2

    def test_evaluate_from_file(self, tmp_path):
        evaluator = Evaluator(model_name="file-model")
        file_path = tmp_path / "preds.json"
        file_path.write_text(json.dumps({
            "dataset_hash": "abc123hash",
            "predictions": [
                {"prediction": "change_pin", "ground_truth": "change_pin", "latency_ms": 30.0, "cost": 0.0001},
                {"prediction": "get_physical_card", "ground_truth": "change_pin", "latency_ms": 35.0, "cost": 0.0001},
            ]
        }))

        result = evaluator.evaluate_from_file(str(file_path))
        assert result.accuracy == 0.5
        assert result.dataset_hash == "abc123hash"
        assert result.total_requests == 2

    def test_save_report(self, tmp_path):
        evaluator = Evaluator(model_name="report-model")
        result = evaluator.evaluate_predictions(
            predictions=["change_pin"],
            ground_truth=["change_pin"],
            latencies=[50.0],
        )
        out_file = tmp_path / "report.json"
        evaluator.save_report(result, str(out_file))

        assert out_file.exists()
        loaded = json.loads(out_file.read_text())
        assert loaded["model_name"] == "report-model"
        assert loaded["accuracy"] == 1.0

    def test_compare_models(self):
        evaluator = Evaluator()
        baseline = EvaluationResult(
            model_name="gpt-4o-mini",
            accuracy=0.92,
            macro_f1=0.91,
            p95_latency_ms=250.0,
            cost_per_1k_queries=0.15,
            invalid_rate=0.01,
        )
        local = EvaluationResult(
            model_name="qwen2.5-1.5b-q4",
            accuracy=0.88,
            macro_f1=0.87,
            p95_latency_ms=60.0,
            cost_per_1k_queries=0.05,
            invalid_rate=0.02,
        )

        comparison = evaluator.compare_models(baseline, local)
        assert comparison["baseline"]["model"] == "gpt-4o-mini"
        assert comparison["local"]["model"] == "qwen2.5-1.5b-q4"
        assert comparison["delta"]["accuracy"] == pytest.approx(-0.04)
        assert comparison["delta"]["latency_reduction_pct"] > 50.0
        assert comparison["delta"]["cost_savings_pct"] > 50.0


class TestModelComparison:
    """Test model comparison and promotion gates."""

    def test_promotion_pass(self):
        comp = ModelComparison(min_accuracy=0.85, max_p95_latency_ms=500.0, max_invalid_rate=0.05)
        res = EvaluationResult(
            model_name="candidate",
            accuracy=0.88,
            p95_latency_ms=120.0,
            invalid_rate=0.01,
        )
        promo = comp.check_promotion(res)
        assert promo["promoted"] is True
        assert promo["checks"]["accuracy"]["passed"] is True
        assert promo["checks"]["p95_latency"]["passed"] is True
        assert promo["checks"]["invalid_rate"]["passed"] is True

    def test_promotion_fail_accuracy(self):
        comp = ModelComparison(min_accuracy=0.85)
        res = EvaluationResult(
            model_name="candidate-low-acc",
            accuracy=0.78,
            p95_latency_ms=120.0,
            invalid_rate=0.01,
        )
        promo = comp.check_promotion(res)
        assert promo["promoted"] is False
        assert promo["checks"]["accuracy"]["passed"] is False

    def test_compare_side_by_side(self):
        comp = ModelComparison()
        baseline = EvaluationResult(model_name="base", accuracy=0.90, p95_latency_ms=200.0, cost_per_1k_queries=0.20)
        candidate = EvaluationResult(model_name="cand", accuracy=0.88, p95_latency_ms=50.0, cost_per_1k_queries=0.05)

        res = comp.compare(baseline, candidate)
        assert "baseline" in res
        assert "candidate" in res
        assert "delta" in res
        assert res["delta"]["cost_savings_pct"] == pytest.approx(75.0)


class TestPredictionRunner:
    """Test the async prediction runner."""

    @pytest.mark.asyncio
    async def test_run_dataset(self):
        runner = PredictionRunner(gateway_url="http://mock-gateway", concurrency=2)
        dataset = [
            {"text": "How do I change my PIN?", "label": "change_pin"},
            {"text": "Change card PIN please", "label": "change_pin"},
        ]

        with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "prediction": "change_pin",
                "route": "local",
                "latency_ms": 25.0,
                "valid_output": True,
            }
            mock_post.return_value = mock_resp

            predictions = await runner.run_predictions(dataset)
            assert len(predictions) == 2
            assert predictions[0]["prediction"] == "change_pin"
            assert predictions[0]["ground_truth"] == "change_pin"
            assert predictions[0]["valid_output"] is True
