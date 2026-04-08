import httpx

from app.services import notification_dispatch_client as client_module


def test_send_email_returns_none_when_service_is_disabled(monkeypatch):
    monkeypatch.setattr(client_module.settings, "NOTIFICATION_SERVICE_URL", None)
    monkeypatch.setattr(client_module.settings, "NOTIFICATION_SERVICE_TOKEN", None)

    delivered = client_module.notification_dispatch_client.send_email(
        to_email="user@example.com",
        subject="Test",
        html_body="<p>Hello</p>",
        text_body="Hello",
    )

    assert delivered is None


def test_send_email_posts_to_notification_service(monkeypatch):
    monkeypatch.setattr(
        client_module.settings,
        "NOTIFICATION_SERVICE_URL",
        "http://notification-service.internal:8010",
    )
    monkeypatch.setattr(client_module.settings, "NOTIFICATION_SERVICE_TOKEN", "test-token")
    monkeypatch.setattr(client_module.settings, "NOTIFICATION_SERVICE_TIMEOUT_SECONDS", 2.5)

    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return httpx.Response(200, json={"delivered": True})

    monkeypatch.setattr(client_module.httpx, "post", fake_post)

    delivered = client_module.notification_dispatch_client.send_email(
        to_email="user@example.com",
        subject="Test",
        html_body="<p>Hello</p>",
        text_body="Hello",
    )

    assert delivered is True
    assert captured["url"] == "http://notification-service.internal:8010/api/v1/notifications/email"
    assert captured["json"]["to_email"] == "user@example.com"
    assert captured["headers"]["Authorization"] == "Bearer test-token"
    assert captured["timeout"] == 2.5


def test_send_email_returns_false_when_notification_service_errors(monkeypatch):
    monkeypatch.setattr(
        client_module.settings,
        "NOTIFICATION_SERVICE_URL",
        "http://notification-service.internal:8010",
    )
    monkeypatch.setattr(client_module.settings, "NOTIFICATION_SERVICE_TOKEN", "test-token")

    def fake_post(url, json, headers, timeout):
        return httpx.Response(503, json={"delivered": False})

    monkeypatch.setattr(client_module.httpx, "post", fake_post)

    delivered = client_module.notification_dispatch_client.send_email(
        to_email="user@example.com",
        subject="Test",
        html_body="<p>Hello</p>",
        text_body="Hello",
    )

    assert delivered is False
