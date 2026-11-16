#!/usr/bin/env bash
# run_failure_demo.sh — Automated failure injection, fallback, and rollback demo runner
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

python3 scripts/run_failure_demo.py

