from app.core.security import verify_password
from app.models.user import User
from app.services import bootstrap_service


def _clear_users(db):
    db.query(User).delete()
    db.commit()


def test_bootstrap_demo_admin_creates_first_admin(db, monkeypatch):
    _clear_users(db)
    monkeypatch.setattr(bootstrap_service.settings, "DEMO_ADMIN_ENABLED", True)
    monkeypatch.setattr(bootstrap_service.settings, "DEMO_ADMIN_EMAIL", "admin@demo.test")
    monkeypatch.setattr(bootstrap_service.settings, "DEMO_ADMIN_PASSWORD", "C1sco12345")
    monkeypatch.setattr(bootstrap_service.settings, "DEMO_ADMIN_FULL_NAME", "Demo Admin")
    monkeypatch.setattr(bootstrap_service.settings, "DEMO_ADMIN_COMPANY_NAME", "Cisco Demo")

    admin = bootstrap_service.bootstrap_demo_admin(db)

    assert admin is not None
    assert admin.email == "admin@demo.test"
    assert admin.account_type == "admin"
    assert admin.status == "active"
    assert admin.email_verified is True
    assert admin.company_name == "Cisco Demo"
    assert verify_password("C1sco12345", admin.password_hash)


def test_bootstrap_demo_admin_is_noop_when_users_exist(db, monkeypatch):
    monkeypatch.setattr(bootstrap_service.settings, "DEMO_ADMIN_ENABLED", True)
    monkeypatch.setattr(bootstrap_service.settings, "DEMO_ADMIN_EMAIL", "admin@demo.test")
    monkeypatch.setattr(bootstrap_service.settings, "DEMO_ADMIN_PASSWORD", "C1sco12345")

    admin = bootstrap_service.bootstrap_demo_admin(db)

    assert admin is None
    assert db.query(User).count() == 1


def test_bootstrap_demo_admin_is_noop_when_disabled(db, monkeypatch):
    _clear_users(db)
    monkeypatch.setattr(bootstrap_service.settings, "DEMO_ADMIN_ENABLED", False)
    monkeypatch.setattr(bootstrap_service.settings, "DEMO_ADMIN_EMAIL", "admin@demo.test")
    monkeypatch.setattr(bootstrap_service.settings, "DEMO_ADMIN_PASSWORD", "C1sco12345")

    admin = bootstrap_service.bootstrap_demo_admin(db)

    assert admin is None
    assert db.query(User).count() == 0
