#!/bin/bash
# Health check for all services
set -e

echo "🏥 Service Health Check"
echo "━━━━━━━━━━━━━━━━━━━━━━"

# Gateway
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
echo -n "Gateway ($GATEWAY_URL): "
if curl -sf "$GATEWAY_URL/health" > /dev/null 2>&1; then
    echo "✅ Healthy"
else
    echo "❌ Unreachable"
fi

# llama.cpp server
LLAMA_URL="${LLAMA_SERVER_URL:-http://localhost:8081}"
echo -n "llama.cpp ($LLAMA_URL): "
if curl -sf "$LLAMA_URL/health" > /dev/null 2>&1; then
    echo "✅ Healthy"
else
    echo "⚠️  Not running (optional)"
fi

# Dashboard
DASHBOARD_URL="${DASHBOARD_URL:-http://localhost:8501}"
echo -n "Dashboard ($DASHBOARD_URL): "
if curl -sf "$DASHBOARD_URL" > /dev/null 2>&1; then
    echo "✅ Running"
else
    echo "⚠️  Not running"
fi

# Database
echo -n "Database: "
if python3 -c "
from sqlalchemy import create_engine, text
import os
url = os.getenv('DATABASE_URL', 'sqlite:///./data/llmops.db').replace('sqlite+aiosqlite', 'sqlite').replace('postgresql+asyncpg', 'postgresql')
engine = create_engine(url)
with engine.connect() as conn:
    conn.execute(text('SELECT 1'))
print('ok')
" 2>/dev/null | grep -q "ok"; then
    echo "✅ Connected"
else
    echo "⚠️  Not available"
fi

