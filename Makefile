.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n",$$1,$$2}'

.PHONY: install
install: ## Install Python and frontend dependencies
	python -m pip install -e ".[dev]"
	cd apps/dashboard && npm install

.PHONY: up
up: ## Bring up the whole stack (infrastructure + services)
	$(COMPOSE) up -d --build

.PHONY: infra
infra: ## Infrastructure only (postgres, kafka, influx, ...)
	$(COMPOSE) up -d postgres influxdb kafka zookeeper mosquitto minio grafana

.PHONY: down
down: ## Stop the stack
	$(COMPOSE) down

.PHONY: logs
logs: ## Follow service logs
	$(COMPOSE) logs -f --tail=100

.PHONY: seed
seed: ## Generate synthetic data and load it into the database (README §10)
	python scripts/seed_synthetic.py

.PHONY: train
train: ## Train the fault detection model and the RUL estimator on synthetic data
	python -m ml.training.train_fault_model
	python -m ml.training.train_rul_model

.PHONY: dashboard
dashboard: ## Run the frontend in development mode
	cd apps/dashboard && npm run dev

.PHONY: lint
lint: ## Check code style
	ruff check services ml scripts
	cd apps/dashboard && npm run lint

.PHONY: test
test: ## Run tests
	pytest
	cd apps/dashboard && npm run test --if-present

.PHONY: fmt
fmt: ## Format code
	ruff check --fix services ml scripts
	ruff format services ml scripts
