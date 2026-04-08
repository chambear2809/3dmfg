# Notification Service

Standalone microservice for outbound email and webhook delivery.

## Run locally

```bash
cd notification-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8010
```

## Endpoints

- `GET /health`
- `POST /api/v1/notifications/email`
- `POST /api/v1/notifications/webhook`

Both notification endpoints require `Authorization: Bearer <INTERNAL_API_TOKEN>`.

## Backend integration

Set these in `backend/.env` to delegate mail delivery:

```bash
NOTIFICATION_SERVICE_URL=http://localhost:8010
NOTIFICATION_SERVICE_TOKEN=change-me-notification-token
```
