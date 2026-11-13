# Known Limitations

## Model & Data
- Fine-tuned model accuracy depends on Colab training quality and may not match commercial API
- Banking77 is a research dataset; real customer messages may differ in distribution
- The golden test set (500 examples) is relatively small for statistical significance per-class

## Infrastructure
- Local model requires llama.cpp installation and model download (~1-2GB)
- Apple Silicon Metal acceleration requires native llama.cpp (not containerized)
- Docker containers may not provide GPU acceleration on macOS
- 16GB RAM limits concurrent inference capacity

## Cost Analysis
- API pricing changes frequently; configured prices may become outdated
- Local cost estimates depend on assumptions about hardware utilization
- Break-even analysis assumes 24/7 operation for local hosting

## Routing & Resilience
- Accuracy-based rollback requires ground-truth labels in requests (evaluation harness only)
- Sticky routing changes assignments when percentages change
- Circuit breaker recovery requires manual reset or timeout

## Evaluation
- Mock baseline provides deterministic but simplified predictions (not real API accuracy)
- Without an API key, baseline evaluation reflects mock behavior only
- Per-class metrics may be unreliable for rare classes with few test examples

## External Dependencies
- OpenAI API key required for real baseline evaluation
- Google Colab required for fine-tuning (not possible on MacBook Air)
- HuggingFace connectivity required for dataset download

