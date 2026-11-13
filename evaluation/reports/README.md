# Evaluation Reports

This directory stores generated evaluation reports from model comparison runs.

## Report Types

| File Pattern | Description |
|---|---|
| `comparison_*.json` | Side-by-side baseline vs. local model evaluation |
| `cost_report_*.json` | Cost analysis with break-even calculations |
| `promotion_gate_*.json` | Model promotion gate pass/fail results |

## Generating Reports

```bash
# Run the evaluation engine
python -m evaluation.evaluate --output evaluation/reports/

# Generate cost analysis
python -m evaluation.cost --output evaluation/reports/
```

Reports are **not committed to Git** — they are generated per-run and may contain environment-specific data.
