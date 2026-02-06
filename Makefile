VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip
PYTEST=$(VENV)/bin/pytest
RUFF=$(VENV)/bin/ruff
MYPY=$(VENV)/bin/mypy

install:
	python3.12 -m venv $(VENV)
	$(PIP) install -U pip setuptools wheel
	$(PIP) install -e '.[dev]'

test:
	$(PYTEST) -q

lint:
	$(RUFF) check app tests ui

typecheck:
	$(MYPY) app

run-api:
	$(VENV)/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-worker:
	$(VENV)/bin/celery -A app.tasks.celery_app worker -Q default,ingest,llm,publish -l info

run-ui:
	API_BASE_URL=http://localhost:8000 $(VENV)/bin/streamlit run ui/app.py

migrate:
	$(VENV)/bin/alembic upgrade head

seed:
	$(PY) scripts/seed_sources.py
