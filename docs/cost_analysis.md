# Cost Analysis Methodology

## Commercial API Cost

```
API query cost = (input_tokens × input_price_per_token) + (output_tokens × output_price_per_token)
```

Default pricing (GPT-4o-mini, as of 2024-07-18):
- Input: $0.15 per 1M tokens
- Output: $0.60 per 1M tokens

Token usage is taken from actual API responses when available, estimated otherwise.

## Local Inference Cost

```
Local cost per query = machine_cost_per_hour / queries_served_per_hour
```

### Scenarios
| Scenario | Machine Cost/Hour | Description |
|----------|------------------|-------------|
| Low | $0.05 | Owned hardware (electricity + depreciation) |
| Base | $0.25 | Small cloud CPU instance |
| High | $1.00 | Cloud GPU instance |

## Break-Even Analysis

```
Monthly API cost = monthly_queries × api_cost_per_query
Monthly local cost = machine_cost_per_hour × 24 × 30 (always-on)
Break-even: monthly_queries = monthly_local_cost / api_cost_per_query
```

The break-even volume represents the monthly query count where local hosting becomes cheaper than API-only.

## Important Notes

- Owned hardware is NOT treated as free — electricity and depreciation are included
- Training cost is shown separately (one-time, ~$0 on free Colab)
- All cost figures are configurable through `configs/pricing.yaml`
- Estimates are clearly labeled; actual API usage data is preferred

