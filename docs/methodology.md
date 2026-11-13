# Evaluation & Experiment Methodology

## Evaluation Metrics

### Primary: Accuracy
Exact-match classification accuracy against Banking77 labels. A prediction is correct only if it exactly matches the ground-truth label after normalization.

### Secondary: Macro-F1
Macro-averaged F1 score across all 77 classes. Gives equal weight to each class regardless of frequency.

### Invalid Output Rate
Percentage of predictions that don't match any of the 77 valid Banking77 labels.

### Latency
- **p50**: Median latency (typical user experience)
- **p95**: 95th percentile (tail latency)
- **Mean**: Average latency

### Cost
- Per-query cost based on actual token usage and configured pricing
- Cost per 1,000 queries for comparison

## Evaluation Protocol

1. All models evaluated against the **same fixed golden test set** (500 examples)
2. Golden set is **never used for training** or checkpoint selection
3. Labels are normalized before comparison (lowercase, underscores, stripped)
4. Invalid outputs are counted but not treated as correct
5. Missing ground-truth labels are excluded from accuracy calculations

## Experiment Design

### Traffic Simulation
- Replay golden test examples through the gateway
- Each experiment has a unique ID and saved configuration
- Results are stored in the database and as JSON files

### Rollback Testing
- Requires minimum labelled samples (default: 30) before accuracy-based rollback
- Error rate and latency rollback don't require ground-truth labels
- Fault injection provides deterministic, reproducible failure scenarios

## Reproducibility

Every evaluation records:
- Dataset SHA-256 hash
- Model identifier
- Git commit SHA
- Routing configuration
- Timestamp
- Random seed (42 for all data splits)

