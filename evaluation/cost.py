"""Cost analysis and break-even calculation engine."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PricingAssumptions:
    """Pricing assumptions for cost calculations."""

    # Commercial API pricing
    api_input_price_per_mtok: float = 0.15   # USD per 1M input tokens
    api_output_price_per_mtok: float = 0.60  # USD per 1M output tokens
    api_avg_input_tokens: float = 800.0
    api_avg_output_tokens: float = 10.0

    # Local inference pricing
    machine_cost_per_hour_low: float = 0.05     # Owned hardware (electricity)
    machine_cost_per_hour_base: float = 0.25    # Small cloud CPU
    machine_cost_per_hour_high: float = 1.00    # Cloud GPU
    local_queries_per_hour: float = 200.0       # Conservative estimate

    # Training cost (one-time)
    training_cost_usd: float = 0.0  # Free tier Colab

    currency: str = "USD"
    source: str = "configurable"


class CostCalculator:
    """Calculate and compare costs between API and local inference."""

    def __init__(self, assumptions: PricingAssumptions | None = None) -> None:
        self.assumptions = assumptions or PricingAssumptions()

    def api_query_cost(
        self,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> float:
        """Cost of a single API query."""
        inp = input_tokens or self.assumptions.api_avg_input_tokens
        out = output_tokens or self.assumptions.api_avg_output_tokens
        input_cost = inp * (self.assumptions.api_input_price_per_mtok / 1_000_000)
        output_cost = out * (self.assumptions.api_output_price_per_mtok / 1_000_000)
        return input_cost + output_cost

    def local_query_cost(self, scenario: str = "base") -> float:
        """Cost of a single local query under a given scenario."""
        cost_map = {
            "low": self.assumptions.machine_cost_per_hour_low,
            "base": self.assumptions.machine_cost_per_hour_base,
            "high": self.assumptions.machine_cost_per_hour_high,
        }
        hourly = cost_map.get(scenario, self.assumptions.machine_cost_per_hour_base)
        qph = max(self.assumptions.local_queries_per_hour, 1)
        return hourly / qph

    def cost_per_1k(self, cost_per_query: float) -> float:
        """Cost per 1,000 queries."""
        return cost_per_query * 1000

    def break_even_monthly_queries(self, scenario: str = "base") -> float | None:
        """Monthly query volume where local becomes cheaper than API.

        Monthly fixed cost is the dedicated hardware amortized or rented 24/7.
        Break-even volume Q* is where monthly API cost (Q * api_cpq) equals
        the monthly fixed cost of running the local inference server:
            Q* = monthly_fixed / api_cpq
        """
        api_cpq = self.api_query_cost()
        if api_cpq <= 0:
            return None

        cost_map = {
            "low": self.assumptions.machine_cost_per_hour_low,
            "base": self.assumptions.machine_cost_per_hour_base,
            "high": self.assumptions.machine_cost_per_hour_high,
        }
        monthly_fixed = cost_map.get(scenario, self.assumptions.machine_cost_per_hour_base) * 24 * 30
        return monthly_fixed / api_cpq

    def sensitivity_analysis(self) -> dict[str, dict[str, float]]:
        """Run cost analysis for low, base, and high scenarios."""
        results: dict[str, dict[str, float]] = {}
        for scenario in ("low", "base", "high"):
            api_cpq = self.api_query_cost()
            local_cpq = self.local_query_cost(scenario)
            be = self.break_even_monthly_queries(scenario)
            results[scenario] = {
                "api_cost_per_query": api_cpq,
                "api_cost_per_1k": self.cost_per_1k(api_cpq),
                "local_cost_per_query": local_cpq,
                "local_cost_per_1k": self.cost_per_1k(local_cpq),
                "break_even_monthly_queries": be if be is not None else -1,
                "savings_at_10k_monthly": (api_cpq * 10000) - (local_cpq * 10000),
            }
        return results

    def generate_report(self) -> dict:
        """Generate a complete cost analysis report."""
        return {
            "assumptions": {
                "api_input_price_per_mtok": self.assumptions.api_input_price_per_mtok,
                "api_output_price_per_mtok": self.assumptions.api_output_price_per_mtok,
                "api_avg_input_tokens": self.assumptions.api_avg_input_tokens,
                "api_avg_output_tokens": self.assumptions.api_avg_output_tokens,
                "local_queries_per_hour": self.assumptions.local_queries_per_hour,
                "training_cost": self.assumptions.training_cost_usd,
                "currency": self.assumptions.currency,
            },
            "per_query": {
                "api": self.api_query_cost(),
                "local_low": self.local_query_cost("low"),
                "local_base": self.local_query_cost("base"),
                "local_high": self.local_query_cost("high"),
            },
            "per_1k": {
                "api": self.cost_per_1k(self.api_query_cost()),
                "local_low": self.cost_per_1k(self.local_query_cost("low")),
                "local_base": self.cost_per_1k(self.local_query_cost("base")),
                "local_high": self.cost_per_1k(self.local_query_cost("high")),
            },
            "sensitivity": self.sensitivity_analysis(),
        }

