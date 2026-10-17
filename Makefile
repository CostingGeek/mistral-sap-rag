# Makefile for SAP Fit-Gap RAG Application

.PHONY: help install dev run lint test clean

# Default target
help:
	@echo "Available targets:"
	@echo "  install   - Install backend dependencies"
	@echo "  dev       - Run backend in development mode"
	@echo "  frontend  - Start frontend development server"
	@echo "  run       - Run full application (backend + frontend)"
	@echo "  lint      - Run linting"
	@echo "  test      - Run tests"
	@echo "  clean     - Clean build artifacts"

# Directory variables
BACKEND_DIR := backend
FRONTEND_DIR := frontend

# Install dependencies
install:
	@echo "Installing backend dependencies..."
	pip install -r $(BACKEND_DIR)/requirements.txt
	@echo "Backend dependencies installed"

# Development
dev:
	@echo "Starting backend server..."
	cd $(BACKEND_DIR) && python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

frontend:
	@echo "Starting frontend development server..."
	cd $(FRONTEND_DIR) && npm install && npm run dev

run: dev

# Linting
lint:
	@echo "Running linting..."
	cd $(BACKEND_DIR) && python -m black --check .
	cd $(BACKEND_DIR) && python -m isort --check .

# Testing
test:
	@echo "Running tests..."
	cd $(BACKEND_DIR) && python -m pytest

# Clean
clean:
	rm -rf $(BACKEND_DIR)/__pycache__
	rm -rf $(BACKEND_DIR)/*.pyc
	rm -rf $(FRONTEND_DIR)/node_modules
	rm -rf $(FRONTEND_DIR)/dist
	rm -rf $(FRONTEND_DIR)/.vite
	rm -rf uploads/
