# Makefile for SAP RAG Chat Application

.PHONY: help install install-dev dev run lint test test-backend test-frontend test-all clean pre-commit secrets-scan test-regression

# Default target
help:
	@echo "Available targets:"
	@echo "  install        - Install backend dependencies"
	@echo "  install-dev    - Install development dependencies (including test deps)"
	@echo "  dev           - Run backend in development mode"
	@echo "  frontend      - Start frontend development server"
	@echo "  run           - Run full application (backend + frontend)"
	@echo "  lint          - Run linting"
	@echo "  test          - Run all tests (backend + frontend)"
	@echo "  test-backend  - Run backend tests only"
	@echo "  test-frontend - Run frontend tests only"
	@echo "  test-all      - Run all tests with coverage"
	@echo "  test-regression - Run regression tests (backend only, simple interface)"
	@echo "  clean         - Clean build artifacts"
	@echo "  pre-commit    - Install pre-commit hooks"
	@echo "  secrets-scan  - Run secret scanner"

# Directory variables
BACKEND_DIR := backend
FRONTEND_DIR := frontend

# Install dependencies
install:
	@echo "Installing backend dependencies..."
	uv sync
	@echo "Backend dependencies installed"

install-dev:
	@echo "Installing backend and development dependencies..."
	uv sync --dev
	@echo "All dependencies installed"

# Development
dev:
	@echo "Starting backend server..."
	uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

frontend:
	@echo "Starting frontend development server..."
	cd $(FRONTEND_DIR) && npm install && npm run dev

run: dev

# Linting
lint:
	@echo "Running linting..."
	cd $(BACKEND_DIR) && uv run python -m black --check .
	cd $(BACKEND_DIR) && uv run python -m isort --check .

# Testing
test: test-backend test-frontend

test-backend:
	@echo "Running backend tests..."
	uv run python -m pytest backend/tests/ -v

test-frontend:
	@echo "Running frontend tests..."
	cd $(FRONTEND_DIR) && npm test

test-all:
	@echo "Running all tests with coverage..."
	uv run python -m pytest backend/tests/ --cov=backend --cov-report=term-missing -v

# Regression tests - simple interface
test-regression:
	@echo "Running regression tests..."
	uv run python backend/tests/run_regression_tests.py

# Pre-commit hooks
pre-commit:
	@echo "Installing pre-commit hooks..."
	uv run pip install pre-commit
	uv run pre-commit install
	@echo "Pre-commit hooks installed. Run 'pre-commit run --all-files' to test."

secrets-scan:
	@echo "Running secret scanner..."
	uv run pre-commit run detect-secrets --all-files

# Clean
clean:
	rm -rf $(BACKEND_DIR)/__pycache__
	rm -rf $(BACKEND_DIR)/*.pyc
	rm -rf $(FRONTEND_DIR)/node_modules
	rm -rf $(FRONTEND_DIR)/dist
	rm -rf $(FRONTEND_DIR)/.vite
	find $(BACKEND_DIR)/tests -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
