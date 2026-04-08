"""Tests for security and trace-response header behavior."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.datastructures import MutableHeaders

from app import main as app_main


def _make_headers(initial_headers: dict[str, str] | None = None) -> MutableHeaders:
    message = {"type": "http.response.start", "status": 200, "headers": []}
    headers = MutableHeaders(scope=message)
    for key, value in (initial_headers or {}).items():
        headers[key] = value
    return headers


def test_apply_trace_response_headers_adds_server_timing_and_expose_header(monkeypatch):
    monkeypatch.setenv("SPLUNK_TRACE_RESPONSE_HEADER_ENABLED", "true")
    monkeypatch.setattr(
        app_main,
        "_build_server_timing_traceparent",
        lambda: 'traceparent;desc="00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01"',
    )

    headers = _make_headers()
    app_main._apply_trace_response_headers(headers)

    assert (
        headers["Server-Timing"]
        == 'traceparent;desc="00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01"'
    )
    assert headers["Access-Control-Expose-Headers"] == "Server-Timing"


def test_apply_trace_response_headers_merges_existing_headers_without_duplicate_traceparent(monkeypatch):
    monkeypatch.setenv("SPLUNK_TRACE_RESPONSE_HEADER_ENABLED", "true")
    monkeypatch.setattr(
        app_main,
        "_build_server_timing_traceparent",
        lambda: 'traceparent;desc="00-cccccccccccccccccccccccccccccccc-dddddddddddddddd-01"',
    )

    headers = _make_headers(
        {
            "Server-Timing": 'cache;dur=12, traceparent;desc="00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01"',
            "Access-Control-Expose-Headers": "X-Request-ID",
        }
    )
    app_main._apply_trace_response_headers(headers)

    assert (
        headers["Server-Timing"]
        == 'cache;dur=12, traceparent;desc="00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01"'
    )
    assert headers["Access-Control-Expose-Headers"] == "X-Request-ID, Server-Timing"


def test_middleware_adds_security_and_server_timing_headers(monkeypatch):
    monkeypatch.setenv("SPLUNK_TRACE_RESPONSE_HEADER_ENABLED", "true")
    monkeypatch.setattr(
        app_main,
        "_build_server_timing_traceparent",
        lambda: 'traceparent;desc="00-eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee-ffffffffffffffff-01"',
    )

    app = FastAPI()
    app.add_middleware(app_main.SecurityHeadersMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/ping")

    assert response.status_code == 200
    assert response.headers["Server-Timing"] == 'traceparent;desc="00-eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee-ffffffffffffffff-01"'
    assert response.headers["Access-Control-Expose-Headers"] == "Server-Timing"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
