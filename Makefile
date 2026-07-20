.PHONY: help install dev install lint test test-verbose test-coverage build clean stats

help: ## Show this help
	@echo "skill-advisor - Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  [36m%-20s[0m %s
", $$1, $$2}'
	@echo ""
	@echo "Usage: make <command>"

install: ## Install the package
	pip install -e .

dev: ## Install with dev dependencies
	pip install -e ".[dev]"
	pip install flake8 pytest-cov

lint: ## Lint code with flake8
	flake8 skill_advisor/ tests/ --max-line-length=100 --count --statistics

test: ## Run tests
	pytest tests/ -v

test-verbose: ## Run tests with verbose output
	pytest tests/ -v -s --tb=long

test-coverage: ## Run tests with coverage report
	pytest tests/ --cov=skill_advisor --cov-report=term-missing --cov-report=html

build: ## Build sdist + wheel
	pip install build
	python -m build

stats: ## Show database statistics
	python -c "from skill_advisor.search import get_stats; import json; print(json.dumps(get_stats(), indent=2, ensure_ascii=False))"

run: ## Run CLI with default query
	python -m skill_advisor.recommender "我是老师"

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
