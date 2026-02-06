# Setup and Bootstrap

This document describes local setup and first-run workflow.

## Prerequisites

- macOS/Linux with Docker installed
- Python 3.12 available (`python3.12 --version`)
- `make` available

## Step 1: Clone and Enter Repo

```bash
git clone <repo-url>
cd longevai-newsletter
```

## Step 2: Configure Environment

```bash
cp .env.example .env
```

Set at minimum:

- `API_AUTH_TOKEN`
- `DATABASE_URL` (for local Docker, default is fine)
- `REDIS_URL` (for local Docker, default is fine)

## Step 3: Install Python Dependencies

```bash
make install
```

This creates `.venv`, upgrades pip tooling, and installs app + dev dependencies.

## Step 4: Start Infrastructure and Services

```bash
docker compose up --build
```

Services started:

- Postgres (`db`)
- Redis (`redis`)
- FastAPI (`api`)
- Celery worker (`worker`)
- Celery beat scheduler (`scheduler`)
- Streamlit UI (`ui`)

## Step 5: Validate Health

- API health: `GET http://localhost:8000/healthz`
- Metrics endpoint: `GET http://localhost:8000/metrics`
- UI: `http://localhost:8501`

## Step 6: Seed Baseline Sources

If API/worker are running locally:

```bash
make seed
```

## Step 7: Run Quality Checks

```bash
make lint
make typecheck
make test
```

## Optional: Run Components Outside Docker

```bash
make run-api
make run-worker
make run-ui
```
