"""
Tests for validate_domain() in security.py — GUARDIAN-001 command injection prevention.

Ensures malicious domain inputs are rejected before reaching subprocess calls
or being embedded in config files (Caddyfile, batch scripts, Vite config).
"""
import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.security import validate_domain


class TestValidDomains:
    """Domains that should pass validation."""

    @pytest.mark.parametrize("domain", [
        "localhost",
        "filaops.local",
        "my-app.example.com",
        "sub.domain.example.co.uk",
        "a.b.c",
        "test123.dev",
        "my-site",
    ])
    def test_valid_domains_accepted(self, domain):
        result = validate_domain(domain)
        assert result == domain.strip().lower()

    def test_strips_whitespace(self):
        assert validate_domain("  example.com  ") == "example.com"

    def test_lowercases(self):
        assert validate_domain("Example.COM") == "example.com"


class TestMaliciousDomains:
    """Domains containing shell metacharacters or injection attempts."""

    @pytest.mark.parametrize("domain", [
        'test"; rm -rf /; echo "',
        "foo;whoami",
        "a|b",
        "$(cmd)",
        "test`id`",
        "x & del /f /q *",
        "domain'--",
        "a<b>c",
        "test\\path",
        "line1\nline2",
        "line1\rline2",
        "a{b}c",
        "test$(echo pwned)",
    ])
    def test_malicious_domains_rejected(self, domain):
        with pytest.raises(HTTPException) as exc_info:
            validate_domain(domain)
        assert exc_info.value.status_code == 400

    def test_empty_domain_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_domain("")
        assert exc_info.value.status_code == 400

    def test_whitespace_only_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_domain("   ")
        assert exc_info.value.status_code == 400

    def test_domain_too_long_rejected(self):
        long_domain = "a" * 254
        with pytest.raises(HTTPException) as exc_info:
            validate_domain(long_domain)
        assert exc_info.value.status_code == 400

    def test_domain_with_spaces_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_domain("my domain.com")
        assert exc_info.value.status_code == 400

    def test_domain_starting_with_hyphen_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_domain("-invalid.com")
        assert exc_info.value.status_code == 400

    def test_domain_ending_with_hyphen_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_domain("invalid-.com")
        assert exc_info.value.status_code == 400
