# Comprehensive Cost Intelligence & Break-Even Modeling

**Project:** Intelligent LLMOps Cost & Latency Governance Platform  
**Target Hardware:** Apple Silicon ARM64 / Private Cloud Hosting  
**Baseline Model:** Commercial API (GPT-4o-mini: \$0.15/MTok input, \$0.60/MTok output)  
**Target Model:** Fine-Tuned SLM (Qwen2.5-1.5B GGUF Q4_K_M on dedicated hardware)  
**Evaluation Date:** November 2026  

---

## 1. Economic Modeling Formulation

When deploying generative and discriminative language models in enterprise operations, organizations face a fundamental tradeoff between **variable token-based pricing (OPEX)** and **fixed hardware amortization (CAPEX/Hosting)**.

### 1.1 Commercial API Cost Formulation
For a commercial LLM API charging per million tokens, the cost per query $c_{\text{API}}$ is expressed as:
$$c_{\text{API}} = \frac{T_{\text{in}} \times P_{\text{in}} + T_{\text{out}} \times P_{\text{out}}}{10^6}$$

Where:
- $T_{\text{in}}$: Average input prompt tokens ($T_{\text{in}} = 800.0$ for few-shot prompt with context).
- $T_{\text{out}}$: Average output completion tokens ($T_{\text{out}} = 10.0$ for intent classification label).
- $P_{\text{in}}$: Price per million input tokens ($P_{\text{in}} = \$0.15$).
- $P_{\text{out}}$: Price per million output tokens ($P_{\text{out}} = \$0.60$).

Substituting our empirical parameters:
$$c_{\text{API}} = \frac{800 \times 0.15 + 10 \times 0.60}{1,000,000} = \frac{120.0 + 6.0}{1,000,000} = \mathbf{\$0.000126 \text{ per query}}$$
$$\text{Cost per 1,000 queries} = \mathbf{\$0.126}$$

Total monthly expenditure for $Q$ queries using the commercial API is:
$$\text{Cost}_{\text{API}}(Q) = Q \times c_{\text{API}} = 0.000126 \times Q$$

---

### 1.2 Local Inference Cost Formulation
Hosting a fine-tuned model locally or on a private virtual machine incurs both fixed monthly infrastructure costs and marginal variable operational costs:
$$\text{Cost}_{\text{Local}}(Q) = M_{\text{fixed}} + \left(\frac{A_{\text{train}}}{12}\right) + Q \times c_{\text{var}}$$

Where:
- $M_{\text{fixed}}$: Monthly infrastructure/hosting expenditure (cloud VM or amortized hardware).
- $A_{\text{train}}$: One-time fine-tuning training expenditure amortized over 12 months (\$0.00 for open weights / free Colab T4).
- $c_{\text{var}}$: Variable cost per query (electricity, marginal network egress; for local Apple Silicon hardware, $c_{\text{var}} \approx \$0.000000$).

---

### 1.3 Break-Even Query Volume Derivation
The break-even point $Q^*$ occurs at the exact query volume where the total monthly cost of the local model equals the commercial API expenditure:
$$\text{Cost}_{\text{API}}(Q^*) = \text{Cost}_{\text{Local}}(Q^*)$$
$$Q^* \times c_{\text{API}} = M_{\text{fixed}} + Q^* \times c_{\text{var}}$$
$$Q^* \left(c_{\text{API}} - c_{\text{var}}\right) = M_{\text{fixed}}$$
$$\mathbf{Q^* = \frac{M_{\text{fixed}}}{c_{\text{API}} - c_{\text{var}}}}$$

When $c_{\text{var}} \ll c_{\text{API}}$, this simplifies directly to:
$$\mathbf{Q^* = \frac{M_{\text{fixed}}}{c_{\text{API}}}}$$

For any monthly query volume $Q > Q^*$, the local fine-tuned model yields net financial profit (cost savings).

---

## 2. Sensitivity Analysis Across Infrastructure Tiers

To account for diverse operational architectures, we evaluate three real-world deployment profiles (`actual_cost_results.json`):

```
Break-Even Volume by Infrastructure Tier
┌──────────────┬───────────────────────────────┬────────────────┬───────────────────────────┬────────────────────┐
│ Scenario     │ Infrastructure Specification   │ Monthly Fixed  │ Break-Even Monthly Q*     │ Break-Even Daily   │
├──────────────┼───────────────────────────────┼────────────────┼───────────────────────────┼────────────────────┤
│ **Low Cost** │ Dedicated Mac Mini M4 (36-mo) │ $36.00 / mo    │ **285,714 queries**       │ 9,524 queries/day  │
│ **Base**     │ Dedicated Cloud 1x V100/A10G  │ $180.00 / mo   │ **1,428,571 queries**     │ 47,619 queries/day │
│ **High Cost**│ Redundant Dual-GPU Private VM │ $720.00 / mo   │ **5,714,286 queries**     │ 190,476 queries/day│
└──────────────┴───────────────────────────────┴────────────────┴───────────────────────────┴────────────────────┘
```

---

## 3. Projected Monthly Net Savings Analysis

The following table projects monthly operating costs and net savings across monthly query volumes ($Q$):

| Monthly Volume ($Q$) | Commercial API Cost | Local Low (\$36/mo) | Savings (Low) | Local Base (\$180/mo) | Savings (Base) | Local High (\$720/mo) | Savings (High) |
|---|---|---|---|---|---|---|---|
| **10,000** | \$1.26 | \$36.00 | -\$34.74 | \$180.00 | -\$178.74 | \$720.00 | -\$718.74 |
| **50,000** | \$6.30 | \$36.00 | -\$29.70 | \$180.00 | -\$173.70 | \$720.00 | -\$713.70 |
| **100,000** | \$12.60 | \$36.00 | -\$23.40 | \$180.00 | -\$167.40 | \$720.00 | -\$707.40 |
| **285,714 (Low Q\*)**| \$36.00 | \$36.00 | **\$0.00** | \$180.00 | -\$144.00 | \$720.00 | -\$684.00 |
| **500,000** | \$63.00 | \$36.00 | **+\$27.00** | \$180.00 | -\$117.00 | \$720.00 | -\$657.00 |
| **1,000,000** | \$126.00 | \$36.00 | **+\$90.00** | \$180.00 | -\$54.00 | \$720.00 | -\$594.00 |
| **1,428,571 (Base Q\*)**| \$180.00 | \$36.00 | **+\$144.00** | \$180.00 | **\$0.00** | \$720.00 | -\$540.00 |
| **2,500,000** | \$315.00 | \$36.00 | **+\$279.00** | \$180.00 | **+\$135.00** | \$720.00 | -\$405.00 |
| **5,000,000** | \$630.00 | \$36.00 | **+\$594.00** | \$180.00 | **+\$450.00** | \$720.00 | -\$90.00 |
| **5,714,286 (High Q\*)**| \$720.00 | \$36.00 | **+\$684.00** | \$180.00 | **+\$540.00** | \$720.00 | **\$0.00** |
| **10,000,000** | \$1,260.00 | \$36.00 | **+\$1,224.00** | \$180.00 | **+\$1,080.00** | \$720.00 | **+\$540.00** |

```
Monthly Cost vs Query Volume (Semi-Log Scale)
$1,400 │                                                   ▲ API ($1,260)
$1,200 │                                                 ╱
$1,000 │                                               ╱
  $800 │                                             ╱ ─── High Fixed ($720)
  $600 │                                           ╱
  $400 │                                         ╱
  $200 │                                       ╱ ──────── Base Fixed ($180)
    $0 └───┴───────────────┴───────────────┴──╱────────── Low Fixed ($36)
       10k                100k            1M              10M Queries/Month
```

---

## 4. Key Takeaways & Recommendations

1. **Volume-Threshold Decision Boundary:** Organizations handling fewer than 285,000 queries/month should remain on commercial pay-per-token APIs to avoid hardware provisioning overhead.
2. **Exponential Margin at Enterprise Scale:** At high operational volumes (10 million queries/month), transitioning to local or private-cloud inference saves **\$1,080.00 to \$1,224.00 per month** (an **85.7% to 97.1% cost reduction**).
3. **Data Sovereignty Dividend:** Beyond direct token savings, local hosting eliminates external compliance audit costs and privacy liabilities under GDPR and HIPAA.

