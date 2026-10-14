.PHONY: help install run test db-init db-migrate db-upgrade db-downgrade db-reset shell routes frontend-install frontend-dev frontend-build frontend-lint clean

FLASK := uv run flask --app run.py
FRONTEND := npm --prefix frontend

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Install/sync dependencies
	uv sync

run: ## Start the dev server (HTTP + WebSocket)
	uv run python run.py

db-init: ## Initialize the migrations directory
	$(FLASK) db init

db-migrate: ## Autogenerate a migration (use m="message")
	$(FLASK) db migrate -m "$(or $(m),migration)"

db-upgrade: ## Apply pending migrations
	$(FLASK) db upgrade

db-downgrade: ## Roll back the last migration
	$(FLASK) db downgrade

db-reset: ## Drop and recreate the database, then apply migrations
	rm -f instance/chat.db chat.db
	$(FLASK) db upgrade

shell: ## Open a Flask shell
	$(FLASK) shell

routes: ## List registered routes
	$(FLASK) routes

test: ## Run the backend test suite
	uv run pytest -q

frontend-install: ## Install frontend dependencies
	$(FRONTEND) install

frontend-dev: ## Start the frontend dev server (proxies API to Flask)
	$(FRONTEND) run dev

frontend-build: ## Build the frontend for production
	$(FRONTEND) run build

frontend-lint: ## Lint the frontend
	$(FRONTEND) run lint

clean: ## Remove caches and the SQLite database
	rm -rf .pytest_cache .ruff_cache __pycache__ app/**/__pycache__ chat.db
