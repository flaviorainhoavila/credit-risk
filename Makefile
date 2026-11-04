PY := .venv/bin/python
DBT := .venv/bin/dbt

.PHONY: setup data build train evaluate report all test lint

setup:
	uv venv --allow-existing --python 3.12 .venv
	uv pip install --python $(PY) -e ".[dev]"

data:
	$(PY) -m credit_risk.download
	$(PY) -m credit_risk.load_raw

build:
	$(DBT) build --project-dir dbt --profiles-dir dbt
	$(PY) -m credit_risk.data_quality
	$(PY) -m credit_risk.split_summary

train:
	@echo "pending: implemented in M3" && exit 1

evaluate:
	@echo "pending: implemented in M3" && exit 1

report:
	@echo "pending: implemented in M3" && exit 1

all: data build train evaluate report

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .
