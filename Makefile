# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                     ArchLens – Project Makefile                         ║
# ╚══════════════════════════════════════════════════════════════════════════╝

.DEFAULT_GOAL := help
SHELL         := cmd.exe
PYTHON        := python
PIP           := pip
NPM           := npm

# ── Colours (Windows-compatible via ANSI) ─────────────────────────────────
CYAN  = \033[0;36m
RESET = \033[0m

.PHONY: help dev dev-backend dev-frontend install install-backend install-frontend \
        test test-backend lint lint-backend lint-frontend clean

## ── Help ──────────────────────────────────────────────────────────────────
help:          ## Show this help message
	@echo.
	@echo  ArchLens Makefile targets:
	@echo.
	@echo  make install       Install all deps (backend + frontend)
	@echo  make dev           Start backend + frontend dev servers
	@echo  make dev-backend   Start only the FastAPI server
	@echo  make dev-frontend  Start only the Vite dev server
	@echo  make test          Run all tests (backend)
	@echo  make lint          Lint all code (ruff + eslint)
	@echo  make clean         Remove build artifacts and caches
	@echo.

## ── Install ───────────────────────────────────────────────────────────────
install: install-backend install-frontend  ## Install all dependencies

install-backend:
	@echo [backend] Installing Python dependencies...
	cd backend && $(PIP) install -r requirements.txt

install-frontend:
	@echo [frontend] Installing Node dependencies...
	cd frontend && $(NPM) ci

## ── Dev Servers ───────────────────────────────────────────────────────────
dev: ## Start both servers concurrently (requires concurrently or two terminals)
	@echo Starting ArchLens backend and frontend...
	@echo Backend -> http://localhost:8000
	@echo Frontend -> http://localhost:5173
	start cmd /k "cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
	start cmd /k "cd frontend && npm run dev"

dev-backend:  ## Start only the FastAPI backend
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:  ## Start only the Vite frontend
	cd frontend && $(NPM) run dev

## ── Tests ─────────────────────────────────────────────────────────────────
test: test-backend  ## Run all tests

test-backend:  ## Run pytest with coverage
	cd backend && $(PYTHON) -m pytest tests/ -v --tb=short --cov=app --cov-report=term-missing

## ── Lint ──────────────────────────────────────────────────────────────────
lint: lint-backend lint-frontend  ## Lint all code

lint-backend:  ## Run ruff linter + formatter check on backend
	cd backend && $(PYTHON) -m ruff check app parsers ingestion tests
	cd backend && $(PYTHON) -m ruff format --check app parsers ingestion tests

lint-frontend:  ## Run eslint on frontend source
	cd frontend && $(NPM) run lint

## ── Clean ─────────────────────────────────────────────────────────────────
clean:  ## Remove all build artifacts and caches
	@if exist backend\.pytest_cache rd /s /q backend\.pytest_cache
	@if exist backend\.ruff_cache   rd /s /q backend\.ruff_cache
	@if exist backend\htmlcov       rd /s /q backend\htmlcov
	@if exist backend\__pycache__   rd /s /q backend\__pycache__
	@if exist frontend\dist         rd /s /q frontend\dist
	@if exist frontend\node_modules rd /s /q frontend\node_modules
	@echo Clean complete.
