# Experiments

## Structure
- `results/` — JSON output from each experiment run
- `runs/` — MLflow run artifacts (excluded from Git)

## Running Experiments
```bash
python -m loadtest.replay --scenario baseline --requests 50
python -m loadtest.replay --all --requests 50
bash scripts/run_experiments.sh
```

Each experiment generates a unique ID and saves results to `results/<experiment_id>.json`.

