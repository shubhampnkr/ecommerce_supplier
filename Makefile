.PHONY: help install install-browsers setup run run-debug run-no-email schedule check test lint format clean

PYTHON  := python
POETRY  := poetry
VENV    := .venv

# ──────────────────────────────────────────────────────────────────────────────
help: ## Show this help message
	@echo ""
	@echo "  🛍️  Meesho Supplier Agent – Makefile"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ──────────────────────────────────────────────────────────────────────────────
install: ## Install all Python dependencies via Poetry
	$(POETRY) install

install-browsers: ## Install Playwright browsers (Chromium)
	$(POETRY) run playwright install chromium
	$(POETRY) run playwright install-deps chromium

setup: install install-browsers ## Full first-time setup
	@if [ ! -f .env ]; then cp .env.example .env; echo "📝 .env created – fill in your credentials!"; fi
	@mkdir -p reports/downloads logs
	@echo "✅ Setup complete. Edit .env then run: make run"

# ──────────────────────────────────────────────────────────────────────────────
run: ## Run full pipeline (scrape → analyse → report → email)
	$(POETRY) run meesho-agent run

run-debug: ## Run with visible browser window (headless=false)
	$(POETRY) run meesho-agent run --debug

run-no-email: ## Run full pipeline but skip email (saves report locally only)
	$(POETRY) run meesho-agent run --skip-email

schedule: ## Start the daily scheduler (runs at REPORT_SCHEDULE_TIME in .env)
	$(POETRY) run meesho-agent schedule

check: ## Validate configuration settings
	$(POETRY) run meesho-agent check

# ──────────────────────────────────────────────────────────────────────────────
test: ## Run all tests
	$(POETRY) run pytest tests/ -v

test-cov: ## Run tests with coverage
	$(POETRY) run pytest tests/ -v --cov=. --cov-report=html

# ──────────────────────────────────────────────────────────────────────────────
lint: ## Lint code with ruff
	$(POETRY) run ruff check .

format: ## Format code with black
	$(POETRY) run black .

typecheck: ## Type-check with mypy
	$(POETRY) run mypy agents/ core/ config/

# ──────────────────────────────────────────────────────────────────────────────
clean: ## Remove generated files, logs, caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info htmlcov/ .coverage
	@echo "🧹 Clean done."

clean-reports: ## Delete downloaded reports
	rm -rf reports/downloads/*
	@echo "🧹 Reports cleared."

clean-logs: ## Delete log files
	rm -rf logs/*.log
	@echo "🧹 Logs cleared."
