"""Tests for cost calculations and break-even analysis."""

import pytest
from evaluation.cost import CostCalculator, PricingAssumptions


class TestCostCalculator:
    def test_api_query_cost(self):
        calc = CostCalculator(PricingAssumptions(
            api_input_price_per_mtok=0.15,
            api_output_price_per_mtok=0.60,
        ))
        cost = calc.api_query_cost(input_tokens=800, output_tokens=10)
        expected = 800 * 0.15 / 1_000_000 + 10 * 0.60 / 1_000_000
        assert abs(cost - expected) < 1e-10

    def test_local_query_cost(self):
        calc = CostCalculator(PricingAssumptions(
            machine_cost_per_hour_base=0.25,
            local_queries_per_hour=200,
        ))
        cost = calc.local_query_cost("base")
        assert abs(cost - 0.25 / 200) < 1e-10

    def test_cost_per_1k(self):
        calc = CostCalculator()
        per_query = 0.001
        assert calc.cost_per_1k(per_query) == 1.0

    def test_break_even_returns_value(self):
        calc = CostCalculator(PricingAssumptions(
            api_input_price_per_mtok=0.15,
            api_output_price_per_mtok=0.60,
            machine_cost_per_hour_base=0.25,
        ))
        be = calc.break_even_monthly_queries("base")
        assert be is None or be > 0

    def test_sensitivity_has_three_scenarios(self):
        calc = CostCalculator()
        result = calc.sensitivity_analysis()
        assert "low" in result
        assert "base" in result
        assert "high" in result

    def test_report_structure(self):
        calc = CostCalculator()
        report = calc.generate_report()
        assert "assumptions" in report
        assert "per_query" in report
        assert "per_1k" in report
        assert "sensitivity" in report

