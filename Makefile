# =============================================================================
# LLMOps Governance Platform - Makefile
# =============================================================================

.DEFAULT_GOAL := help

PYTHON := python3
PIP := pip
SRC_DIR := src
TEST_DIR := tests
GATEWAY_MODULE := llmops_governance.api.gateway
DASHBOARD_ENTRY := src/llmops_governance/dashboard/app.py

# Colors for terminal output
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RESET := \033[0m

# =============================================================================
# Setup & Installation
# =============================================================================

.PHONY: setup
setup: ## Create virtual environment and install all dependencies
	@echo "$(BLUE)>>> Creating virtual environment...$(RESET)"
	$(PYTHON) -m venv .venv
	@echo "$(BLUE)>>> Installing dependencies...$(RESET)"
	.venv/bin/pip install --upgrade pip setuptools wheel
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pip install -e ".[dev]"
	@echo "$(BLUE)>>> Installing pre-commit hooks...$(RESET)"
	.venv/bin/pre-commit install || true
	@echo "$(GREEN)>>> Setup complete! Activate with: source .venv/bin/activate$(RESET)"

.PHONY: install
install: ## Install package in development mode
	@echo "$(BLUE)>>> Installing package in editable mode...$(RESET)"
	$(PIP) install -e ".[dev]"

# =============================================================================
# Testing
# =============================================================================

.PHONY: test
test: ## Run all tests with coverage
	@echo "$(BLUE)>>> Running tests...$(RESET)"
	$(PYTHON) -m pytest $(TEST_DIR) \
		--cov=$(SRC_DIR)/llmops_governance \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		-v --tb=short

.PHONY: test-unit
test-unit: ## Run unit tests only
	@echo "$(BLUE)>>> Running unit tests...$(RESET)"
	$(PYTHON) -m pytest $(TEST_DIR) -m unit -v --tb=short

.PHONY: test-integration
test-integration: ## Run integration tests only
	@echo "$(BLUE)>>> Running integration tests...$(RESET)"
	$(PYTHON) -m pytest $(TEST_DIR) -m integration -v --tb=short

# =============================================================================
# Code Quality
# =============================================================================

.PHONY: lint
lint: ## Run linting checks (ruff + mypy)
	@echo "$(BLUE)>>> Running ruff linter...$(RESET)"
	$(PYTHON) -m ruff check $(SRC_DIR) $(TEST_DIR)
	@echo "$(BLUE)>>> Running mypy type checker...$(RESET)"
	$(PYTHON) -m mypy $(SRC_DIR) --ignore-missing-imports

.PHONY: format
format: ## Auto-format code with ruff
	@echo "$(BLUE)>>> Formatting code with ruff...$(RESET)"
	$(PYTHON) -m ruff format $(SRC_DIR) $(TEST_DIR)
	$(PYTHON) -m ruff check --fix $(SRC_DIR) $(TEST_DIR)
	@echo "$(GREEN)>>> Formatting complete!$(RESET)"

# =============================================================================
# Run Services
# =============================================================================

.PHONY: run-gateway
run-gateway: ## Start the API gateway server
	@echo "$(BLUE)>>> Starting API Gateway on http://localhost:8000 ...$(RESET)"
	$(PYTHON) -m uvicorn $(GATEWAY_MODULE):app \
		--host 0.0.0.0 \
		--port 8000 \
		--reload \
		--log-level info

.PHONY: run-dashboard
run-dashboard: ## Start the Streamlit dashboard
	@echo "$(BLUE)>>> Starting Streamlit Dashboard on http://localhost:8501 ...$(RESET)"
	$(PYTHON) -m streamlit run $(DASHBOARD_ENTRY) \
		--server.port 8501 \
		--server.address 0.0.0.0 \
		--theme.primaryColor "#1f77b4"

.PHONY: run-mlflow
run-mlflow: ## Start MLflow tracking server
	@echo "$(BLUE)>>> Starting MLflow Tracking Server on http://localhost:5000 ...$(RESET)"
	$(PYTHON) -m mlflow server \
		--backend-store-uri sqlite:///data/mlflow.db \
		--default-artifact-root ./mlartifacts \
		--host 0.0.0.0 \
		--port 5000

# =============================================================================
# Data Pipeline
# =============================================================================

.PHONY: download-data
download-data: ## Download the Banking77 dataset
	@echo "$(BLUE)>>> Downloading Banking77 dataset...$(RESET)"
	$(PYTHON) -c "\
		from datasets import load_dataset; \
		import os; \
		os.makedirs('data/raw', exist_ok=True); \
		ds = load_dataset('PolyAI/banking77'); \
		ds.save_to_disk('data/raw/banking77'); \
		print('Dataset saved to data/raw/banking77')"
	@echo "$(GREEN)>>> Download complete!$(RESET)"

.PHONY: prepare-data
prepare-data: ## Prepare and preprocess the dataset
	@echo "$(BLUE)>>> Preparing dataset...$(RESET)"
	$(PYTHON) -m llmops_governance.cli prepare-data \
		--input-dir data/raw/banking77 \
		--output-dir data/processed
	@echo "$(GREEN)>>> Data preparation complete!$(RESET)"

# =============================================================================
# Evaluation
# =============================================================================

.PHONY: evaluate
evaluate: ## Run model evaluation pipeline
	@echo "$(BLUE)>>> Running evaluation pipeline...$(RESET)"
	$(PYTHON) -m llmops_governance.cli evaluate \
		--config configs/evaluation.yaml \
		--output-dir experiments/results
	@echo "$(GREEN)>>> Evaluation complete! Results in experiments/results/$(RESET)"

# =============================================================================
# Docker
# =============================================================================

.PHONY: docker-build
docker-build: ## Build Docker images
	@echo "$(BLUE)>>> Building Docker images...$(RESET)"
	docker compose build

.PHONY: docker-up
docker-up: ## Start all services with Docker Compose
	@echo "$(BLUE)>>> Starting services with Docker Compose...$(RESET)"
	docker compose up -d
	@echo "$(GREEN)>>> Services started! Gateway: http://localhost:8000 | Dashboard: http://localhost:8501$(RESET)"

.PHONY: docker-down
docker-down: ## Stop all Docker Compose services
	@echo "$(BLUE)>>> Stopping Docker Compose services...$(RESET)"
	docker compose down -v

# =============================================================================
# Cleanup
# =============================================================================

.PHONY: clean
clean: ## Remove build artifacts, caches, and temporary files
	@echo "$(YELLOW)>>> Cleaning build artifacts...$(RESET)"
	rm -rf build/ dist/ *.egg-info .eggs/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf htmlcov/ .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)>>> Clean complete!$(RESET)"

# =============================================================================
# Help
# =============================================================================

.PHONY: help
help: ## Show this help message
	@echo ""
	@echo "$(BLUE)LLMOps Governance Platform$(RESET)"
	@echo "$(BLUE)==========================$(RESET)"
	@echo ""
	@echo "Available targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
