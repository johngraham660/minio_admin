# Makefile for minio_admin project
# Python testing and code quality automation

# Python environment settings
PYTHON = .venv/bin/python
PIP = .venv/bin/pip

.PHONY: help install test test-unit test-integration test-coverage test-all lint clean check-env setup-venv

# Default target
help:
	@echo "Available targets:"
	@echo "  help              - Show this help message"
	@echo "  setup-venv        - Create and setup Python virtual environment"
	@echo "  install           - Install project dependencies"
	@echo "  check-env         - Check if virtual environment is activated"
	@echo "  test              - Run all tests"
	@echo "  test-unit         - Run unit tests only"
	@echo "  test-integration  - Run integration tests only"
	@echo "  test-coverage     - Run all tests with coverage report"
	@echo "  test-all          - Run tests, coverage, and linting (strict)"
	@echo "  test-dev          - Run tests and coverage with non-blocking lint"
	@echo "  lint              - Run code quality checks (flake8)"
	@echo "  clean             - Clean up generated files and cache"

# Setup virtual environment
setup-venv:
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv .venv; \
		echo "Virtual environment created."; \
	else \
		echo "Virtual environment already exists."; \
	fi

# Check if virtual environment is activated
check-env:
	@if [ ! -d ".venv" ]; then \
		echo "Virtual environment not found. Run 'make setup-venv' first."; \
		exit 1; \
	else \
		echo "Virtual environment found: .venv"; \
	fi

# Install dependencies
install: check-env
	@echo "Installing dependencies..."
	$(PIP) install -r requirements.txt

# Run all tests
test: check-env
	@echo "========================================="
	@echo "Running All Tests"
	@echo "========================================="
	$(PYTHON) -m pytest tests/ -v

# Run unit tests only
test-unit: check-env
	@echo "========================================="
	@echo "Running Unit Tests"
	@echo "========================================="
	$(PYTHON) -m pytest tests/ -m unit -v

# Run integration tests only
test-integration: check-env
	@echo "========================================="
	@echo "Running Integration Tests"
	@echo "========================================="
	$(PYTHON) -m pytest tests/ -m integration -v

# Run tests with coverage
test-coverage: check-env
	@echo "========================================="
	@echo "Running All Tests with Coverage"
	@echo "========================================="
	$(PYTHON) -m pytest tests/ --cov=src --cov-report=html --cov-report=term-missing --cov-report=xml -v
	@echo ""
	@echo "Coverage report generated:"
	@echo "  - HTML: htmlcov/index.html"
	@echo "  - XML:  coverage.xml"

# Run code quality checks
lint: check-env
	@echo "========================================="
	@echo "Running Code Quality Checks (flake8)"
	@echo "========================================="
	$(PYTHON) -m flake8 src/ tests/ --max-line-length=100 --ignore=E203,W503 --statistics

# Run everything: tests, coverage, and linting
test-all: test-coverage lint
	@echo ""
	@echo "========================================="
	@echo "All checks completed successfully!"
	@echo "========================================="

# Run tests and linting but don't fail on lint errors (for development)
test-dev: test-coverage
	@echo ""
	@echo "========================================="
	@echo "Running Code Quality Checks (non-blocking)"
	@echo "========================================="
	-$(PYTHON) -m flake8 src/ tests/ --max-line-length=100 --ignore=E203,W503 --statistics
	@echo ""
	@echo "========================================="
	@echo "Development checks completed!"
	@echo "Note: Fix linting issues when ready to commit"
	@echo "========================================="

# Clean up generated files
clean:
	@echo "Cleaning up generated files..."
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "Cleanup completed."

# Quick test run (unit tests only, no coverage)
quick: test-unit

# Continuous integration target
ci: setup-venv install test-coverage lint
	@echo "CI pipeline completed successfully!"

# Development workflow target
dev: setup-venv install test-dev
	@echo "Development setup and testing completed!"