# End-to-End System Reproducibility Guide

**Project:** Intelligent LLMOps Cost & Latency Governance Platform  
**Target Environments:** macOS (Apple Silicon ARM64 / M1-M4) & Linux (x86_64 / Ubuntu 22.04+)  
**Repository:** [github.com/hetsoni1313/MLSE-Project](https://github.com/hetsoni1313/MLSE-Project)  
**Verification Date:** November 2026  

---

## 1. System Requirements and Prerequisites

| Component | Minimum Specification | Recommended Specification |
|---|---|---|
| **Operating System** | macOS 14+ (ARM64) or Ubuntu 22.04+ | macOS Sonoma / Sequoia (M-Series) |
| **Processor** | 4-Core CPU | Apple Silicon (M1/M2/M3/M4) or 8-Core Intel/AMD |
| **RAM** | 8 GB Unified Memory / RAM | 16 GB Unified Memory |
| **Disk Space** | 5 GB free SSD space | 15 GB free SSD space |
| **Python Version**| Python 3.11, 3.12, or 3.13 | Python 3.13 |
| **Container Engine**| Docker 24+ & Docker Compose v2 | Docker Desktop 4.30+ |

---

## 2. Fast-Path Setup (Ready in 3 Minutes)

Execute the following commands in sequence to clone, configure, and install the complete environment:

```bash
# 1. Clone repository
git clone https://github.com/hetsoni1313/MLSE-Project.git
cd MLSE-Project

# 2. Create isolated virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Upgrade pip and install package in editable development mode
pip install --upgrade pip
pip install -e ".[dev]"

# 4. Copy environment configuration
cp .env.example .env
```

---

## 3. Verification & Automated Test Suite

Verify that all components, routing modules, fault injection mechanisms, and database abstractions are operating correctly:

```bash
# Run the complete test suite with coverage report
pytest tests/ --cov=src/llmops_governance --cov=gateway --cov=evaluation --cov-report=term-missing
```

**Expected Result:**
```
TOTAL: 124 passed in < 1.0s
Required test coverage of 80.0% reached. Total coverage: 82.99%
```

### Validate Complete System Architecture
Execute the automated structural and integrity validator:
```bash
bash scripts/validate_project.sh
```
**Expected Result:**
```
RESULTS: 108 passed, 0 failed, 0 warnings
All tests passed
```

---

## 4. Reproducing Resilience, Failure Injection & Rollback Demo

To reproduce the automated 6-stage resilience demonstration (including baseline, shadow mode, canary rollout, transparent fallback during crash, and autonomous rollback upon quality degradation):

```bash
# Execute the automated Python runner
python scripts/run_failure_demo.py

# Alternatively, run the shell runner
bash scripts/run_failure_demo.sh
```

**Outputs Produced:**
- Real-time terminal log detailing each phase.
- Updated raw audit artifact: `submission/results/actual_rollback_events.json`.

---

## 5. Reproducing Benchmarks and Load Tests

To reproduce the 7-scenario load test suite and model evaluation:

```bash
# Execute load test and evaluation harness
python scripts/run_benchmarks_and_loadtest.py
```

**Outputs Produced:**
- `submission/results/actual_loadtest_results.json`: Throughput, p50/p95 latency, and fallback counts.
- `submission/results/actual_evaluation.json`: Golden test set accuracy, Macro-F1, and per-class metrics.
- `submission/results/actual_cost_results.json`: Sensitivity break-even calculations.

---

## 6. Running the Interactive Streamlit Dashboard

To inspect real-time governance metrics, cost breakdowns, routing controls, and audit event logs:

```bash
# Launch Streamlit dashboard
streamlit run dashboard/app.py
```
Open your browser to: `http://localhost:8501`

**Available Dashboard Pages:**
1. **Executive Overview:** High-level KPIs, model distribution, net savings.
2. **Model Performance:** Side-by-side comparison of baseline vs local model, confusion matrix.
3. **Latency & Throughput:** Real-time $p_{50}, p_{95}, p_{99}$ latency distributions and QPS trends.
4. **Cost Intelligence:** Interactive break-even volume calculator and sensitivity tables.
5. **Routing & Reliability:** Dynamic routing control (Canary, Weighted, Shadow) and Circuit Breaker status.
6. **Experiments:** Historical MLflow and local evaluation experiment comparison.

---

## 7. Running the FastAPI Gateway Service

To run the live HTTP inference gateway locally:

```bash
# Start gateway on port 8000
uvicorn gateway.main:app --host 0.0.0.0 --port 8000 --reload
```

Test inference endpoint:
```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"text": "Why was my credit card declined?", "user_id": "demo_user_1"}'
```

---

## 8. Full Containerized Deployment (Docker Compose)

To run the complete production stack (PostgreSQL, Gateway, Dashboard, llama.cpp):

```bash
# Start full containerized stack
docker compose up -d

# Verify container status
docker compose ps

# View service logs
docker compose logs -f gateway
```

**Service Endpoints:**
- Gateway API: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`
- Streamlit Dashboard: `http://localhost:8501`
- llama.cpp Server: `http://localhost:8081`
- PostgreSQL: `localhost:5432`

---

## 9. Reproducing Dataset Preprocessing & Training

### Dataset Download & Partitioning:
```bash
# Download Banking77 dataset from Hugging Face
python scripts/download_data.py

# Format into train (9,503), validation (500), and golden test (500) splits
python scripts/prepare_data.py
```

### Model Fine-Tuning (Google Colab / Cloud GPU):
Due to the memory constraints of local workstations, fine-tuning Qwen2.5-1.5B with LoRA/QLoRA is optimized for free Google Colab T4 GPUs:
1. Open `training/notebooks/colab_finetuning.ipynb` in Google Colab.
2. Select **Runtime > Change runtime type > T4 GPU**.
3. Execute all cells to run QLoRA fine-tuning with Hugging Face PEFT / Unsloth.
4. Download the resulting merged GGUF checkpoint `qwen2.5-1.5b-banking77-q4_k_m.gguf` to `models/`.

### Local Inference Server:
```bash
# Launch llama.cpp server with Metal acceleration
bash scripts/start_server.sh
```
