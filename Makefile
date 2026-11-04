PY := .venv/bin/python
export MLFLOW_DISABLE_AGENT_HINT := 1
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
	$(PY) -m credit_risk.train

evaluate:
	$(PY) -m credit_risk.evaluate

report:
	$(PY) -m credit_risk.report

all: data build train evaluate report

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .
