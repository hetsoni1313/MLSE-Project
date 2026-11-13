#!/usr/bin/env bash
# validate_project.sh — Comprehensive project validation script
# Checks that all expected files exist, tests pass, and the project is buildable.

set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0
WARN=0

pass() { echo -e "  ${GREEN}✓${NC} $1"; PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}✗${NC} $1"; FAIL=$((FAIL + 1)); }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; WARN=$((WARN + 1)); }

echo "============================================================"
echo "LLMOps Governance Platform — Project Validation"
echo "============================================================"
echo ""

# ── 1. Core project files ──────────────────────────────────────
echo "1. Core project files"
for f in pyproject.toml requirements.txt README.md LICENSE Makefile \
         .gitignore .env.example compose.yaml Dockerfile; do
    [ -f "$f" ] && pass "$f" || fail "$f missing"
done
echo ""

# ── 2. Configuration files ─────────────────────────────────────
echo "2. Configuration files"
for f in configs/default.yaml configs/routing.yaml configs/thresholds.yaml \
         configs/pricing.yaml configs/model.yaml configs/logging.yaml; do
    [ -f "$f" ] && pass "$f" || fail "$f missing"
done
echo ""

# ── 3. Core library ────────────────────────────────────────────
echo "3. Core library (src/llmops_governance/)"
for f in src/llmops_governance/__init__.py \
         src/llmops_governance/config/settings.py \
         src/llmops_governance/core/constants.py \
         src/llmops_governance/core/exceptions.py \
         src/llmops_governance/schemas/requests.py \
         src/llmops_governance/schemas/metrics.py \
         src/llmops_governance/utils/validation.py \
         src/llmops_governance/utils/hashing.py \
         src/llmops_governance/utils/timing.py \
         src/llmops_governance/logging/setup.py \
         src/llmops_governance/metrics/database.py \
         src/llmops_governance/metrics/models.py \
         src/llmops_governance/metrics/repository.py \
         src/llmops_governance/metrics/collector.py; do
    [ -f "$f" ] && pass "$f" || fail "$f missing"
done
echo ""

# ── 4. Gateway ─────────────────────────────────────────────────
echo "4. Gateway"
for f in gateway/main.py \
         gateway/api/classify.py gateway/api/health.py \
         gateway/api/admin.py gateway/api/metrics_api.py \
         gateway/backends/__init__.py gateway/backends/baseline.py \
         gateway/backends/local.py gateway/backends/fault_injection.py \
         gateway/routing/engine.py gateway/routing/config.py \
         gateway/resilience/fallback.py gateway/resilience/rollback.py \
         gateway/resilience/circuit_breaker.py \
         gateway/middleware/auth.py gateway/services/__init__.py; do
    [ -f "$f" ] && pass "$f" || fail "$f missing"
done
echo ""

# ── 5. Evaluation ──────────────────────────────────────────────
echo "5. Evaluation"
for f in evaluation/metrics.py evaluation/cost.py evaluation/evaluate.py \
         evaluation/predictions.py evaluation/comparison.py; do
    [ -f "$f" ] && pass "$f" || fail "$f missing"
done
echo ""

# ── 6. Dashboard ───────────────────────────────────────────────
echo "6. Dashboard"
for f in dashboard/app.py \
         dashboard/pages/executive_overview.py \
         dashboard/pages/model_performance.py \
         dashboard/pages/latency_throughput.py \
         dashboard/pages/cost_intelligence.py \
         dashboard/pages/routing_reliability.py \
         dashboard/pages/experiments.py \
         dashboard/services/db_service.py \
         dashboard/components/kpi_cards.py; do
    [ -f "$f" ] && pass "$f" || fail "$f missing"
done
echo ""

# ── 7. Training ────────────────────────────────────────────────
echo "7. Training"
for f in training/train.py training/dataset.py training/format_data.py \
         training/evaluate_checkpoint.py training/config.yaml \
         training/notebooks/colab_finetuning.ipynb; do
    [ -f "$f" ] && pass "$f" || fail "$f missing"
done
echo ""

# ── 8. Load testing ────────────────────────────────────────────
echo "8. Load testing"
for f in loadtest/replay.py loadtest/config.yaml; do
    [ -f "$f" ] && pass "$f" || fail "$f missing"
done
echo ""

# ── 9. Scripts ─────────────────────────────────────────────────
echo "9. Scripts"
for f in scripts/setup.sh scripts/download_data.py scripts/prepare_data.py \
         scripts/start_server.sh scripts/convert_to_gguf.sh \
         scripts/quantize_model.sh scripts/run_experiments.sh \
         scripts/healthcheck.sh; do
    [ -f "$f" ] && pass "$f" || fail "$f missing"
    if [ -f "$f" ] && [[ "$f" == *.sh ]] && [ ! -x "$f" ]; then
        warn "$f is not executable"
    fi
done
echo ""

# ── 10. Tests ──────────────────────────────────────────────────
echo "10. Tests"
for f in tests/conftest.py \
         tests/unit/test_validation.py tests/unit/test_hashing.py \
         tests/unit/test_metrics.py tests/unit/test_cost.py \
         tests/routing/test_weighted.py tests/routing/test_sticky.py \
         tests/routing/test_shadow.py tests/routing/test_canary.py \
         tests/routing/test_config.py \
         tests/resilience/test_fallback.py tests/resilience/test_rollback.py \
         tests/resilience/test_circuit_breaker.py \
         tests/integration/test_gateway.py; do
    [ -f "$f" ] && pass "$f" || fail "$f missing"
done
echo ""

# ── 11. CI/CD ──────────────────────────────────────────────────
echo "11. CI/CD"
for f in .github/workflows/ci.yml .github/workflows/model-promotion.yml; do
    [ -f "$f" ] && pass "$f" || fail "$f missing"
done
echo ""

# ── 12. Docker ─────────────────────────────────────────────────
echo "12. Docker"
for f in Dockerfile compose.yaml infra/docker/Dockerfile.dashboard; do
    [ -f "$f" ] && pass "$f" || fail "$f missing"
done
echo ""

# ── 13. Documentation ─────────────────────────────────────────
echo "13. Documentation"
for f in docs/architecture.md docs/system_design.md docs/methodology.md \
         docs/data_dictionary.md docs/cost_analysis.md docs/deployment.md \
         docs/troubleshooting.md docs/limitations.md \
         docs/demo_script.md docs/experiment_results.md \
         docs/implementation_decisions.md; do
    [ -f "$f" ] && pass "$f" || fail "$f missing"
done
echo ""

# ── 14. Test fixtures ──────────────────────────────────────────
echo "14. Test fixtures"
for f in tests/fixtures/sample_predictions.json tests/fixtures/golden_sample.json; do
    [ -f "$f" ] && pass "$f" || fail "$f missing"
done
echo ""

# ── 15. Run tests (if venv available) ──────────────────────────
echo "15. Running test suite..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    if python -m pytest tests/ -q --tb=line 2>&1; then
        pass "All tests passed"
    else
        fail "Some tests failed"
    fi
else
    warn "Virtual environment not found — skipping test run"
fi
echo ""

# ── Summary ────────────────────────────────────────────────────
echo "============================================================"
echo -e "RESULTS: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}, ${YELLOW}${WARN} warnings${NC}"
echo "============================================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
