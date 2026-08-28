.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help
help: ## نمایش این راهنما
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n",$$1,$$2}'

.PHONY: install
install: ## نصب وابستگی‌های پایتون و فرانت‌اند
	python -m pip install -e ".[dev]"
	cd apps/dashboard && npm install

.PHONY: up
up: ## بالا آوردن کل پشته (زیرساخت + سرویس‌ها)
	$(COMPOSE) up -d --build

.PHONY: infra
infra: ## فقط زیرساخت (postgres, kafka, influx, ...)
	$(COMPOSE) up -d postgres influxdb kafka zookeeper mosquitto minio grafana

.PHONY: down
down: ## توقف پشته
	$(COMPOSE) down

.PHONY: logs
logs: ## دنبال کردن لاگ سرویس‌ها
	$(COMPOSE) logs -f --tail=100

.PHONY: seed
seed: ## تولید داده‌ی سنتتیک و بارگذاری در پایگاه داده (README §۱۰)
	python scripts/seed_synthetic.py

.PHONY: train
train: ## آموزش مدل تشخیص عیب و تخمین‌گر RUL روی داده‌ی سنتتیک
	python -m ml.training.train_fault_model
	python -m ml.training.train_rul_model

.PHONY: dashboard
dashboard: ## اجرای فرانت‌اند در حالت توسعه
	cd apps/dashboard && npm run dev

.PHONY: lint
lint: ## بررسی سبک کد
	ruff check services ml scripts
	cd apps/dashboard && npm run lint

.PHONY: test
test: ## اجرای تست‌ها
	pytest
	cd apps/dashboard && npm run test --if-present

.PHONY: fmt
fmt: ## قالب‌بندی کد
	ruff check --fix services ml scripts
	ruff format services ml scripts
