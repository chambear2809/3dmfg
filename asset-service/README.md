# Asset Service

Standalone microservice for product and quote image storage.

## Run locally

```bash
cd asset-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8020
```

## Endpoints

- `GET /health`
- `POST /api/v1/assets/upload`
- `GET /api/v1/assets/{category}/{asset_key}`
- `DELETE /api/v1/assets/{category}/{asset_key}`

Asset endpoints require `Authorization: Bearer <INTERNAL_API_TOKEN>`.

## Backend integration

Set these in `backend/.env` to delegate image storage:

```bash
ASSET_SERVICE_URL=http://localhost:8020
ASSET_SERVICE_TOKEN=change-me-asset-token
```
