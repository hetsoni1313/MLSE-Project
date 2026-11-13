#!/bin/bash
# Run all experiment scenarios
set -e

GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
ADMIN_KEY="${ADMIN_API_KEY:-change-me-in-production}"
REQUESTS="${NUM_REQUESTS:-50}"
CONCURRENCY="${CONCURRENCY:-2}"

echo "🧪 LLMOps Experiment Runner"
echo "   Gateway: $GATEWAY_URL"
echo "   Requests per scenario: $REQUESTS"
echo ""

# Check gateway is running
if ! curl -sf "$GATEWAY_URL/health" > /dev/null 2>&1; then
    echo "❌ Gateway not responding at $GATEWAY_URL"
    echo "   Start it with: make run-gateway"
    exit 1
fi

echo "✅ Gateway is healthy"
echo ""

for scenario in baseline shadow canary_10 canary_50 full_local; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    python -m loadtest.replay --scenario "$scenario" --gateway "$GATEWAY_URL" --admin-key "$ADMIN_KEY" --requests "$REQUESTS" --concurrency "$CONCURRENCY"
    echo ""
    sleep 2
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All scenarios complete!"
echo "📊 Results saved in experiments/results/"

