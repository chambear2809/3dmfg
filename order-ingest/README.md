# Order Ingest Service

Standalone microservice for CSV parsing and normalization of external sales orders.

## Run locally

```bash
cd order-ingest
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8030
```

## Endpoints

- `GET /health`
- `POST /api/v1/order-ingest/parse-csv`

The parse endpoint requires `Authorization: Bearer <INTERNAL_API_TOKEN>`.

## Backend integration

Set these in `backend/.env` to delegate order CSV parsing:

```bash
ORDER_INGEST_SERVICE_URL=http://localhost:8030
ORDER_INGEST_SERVICE_TOKEN=change-me-order-ingest-token
```
