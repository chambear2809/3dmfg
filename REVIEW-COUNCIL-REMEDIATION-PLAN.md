# FilaOps Review Council Remediation Plan

**Generated:** 2026-01-31
**Target:** Fix all 71 findings, achieve >80% test coverage
**Source:** Review Council findings in `.review-council/reviews/`
**GitHub Issues:** See `.github/ISSUES.md` or run `.github/create-issues.ps1`

---

## How to Use This Plan

### For AI Assistants (VS Code Copilot, Cursor, Windsurf, etc.)

1. **Read the finding** - Each section contains the exact file, line numbers, and code changes needed
2. **Implement the fix** - Follow the code examples provided
3. **Write tests** - If the finding is test-related, use the test templates provided
4. **Mark complete** - Update the checkbox in the "Quick Reference" section at the bottom
5. **Update GitHub issue** - If issues were created, close the corresponding issue

### Workflow for Each Fix

```
1. Read finding details
2. Open the target file(s)
3. Make the changes as specified
4. Run tests: pytest tests/ -v (backend) or npm test (frontend)
5. Update this file: check the box in Quick Reference section
6. Commit with message: "fix(AGENT-ID): Brief description"
   Example: "fix(GUARDIAN-001): Sanitize domain input to prevent command injection"
```

### Closing GitHub Issues

After fixing, close the GitHub issue with:
```bash
gh issue close <issue-number> --comment "Fixed in commit <sha>. See REVIEW-COUNCIL-REMEDIATION-PLAN.md"
```

Or via PR that references: `Fixes #<issue-number>`

---

## Executive Summary

| Severity | Count | Status |
|----------|-------|--------|
| BLOCKER | 5 | ⬜ Pending |
| HIGH | 22 | ⬜ Pending |
| MEDIUM | 27 | ⬜ Pending |
| LOW | 17 | ⬜ Pending |
| **TOTAL** | **71** | |

**Current Test Coverage:** ~20% (estimated)
**Target Test Coverage:** >80%

---

## Phase 1: Critical Security Fixes (BLOCKERS)

### 1.1 GUARDIAN-001: Command Injection in HTTPS Setup [BLOCKER]

**File:** `backend/app/api/v1/endpoints/security.py:785-992`

**Task:** Sanitize domain parameter to prevent shell injection.

```python
# Add this validation function at top of file
import re

def validate_domain(domain: str) -> str:
    """Validate domain against strict pattern to prevent injection."""
    domain = domain.strip().lower()
    if not domain:
        raise HTTPException(status_code=400, detail="Domain cannot be empty")
    
    # Strict domain pattern: letters, numbers, dots, hyphens only
    pattern = r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*$'
    if not re.match(pattern, domain):
        raise HTTPException(status_code=400, detail="Invalid domain format")
    
    # Reject any shell metacharacters as extra safety
    dangerous_chars = ['"', "'", ';', '&', '|', '$', '`', '(', ')', '{', '}', '<', '>', '\\', '\n', '\r']
    if any(char in domain for char in dangerous_chars):
        raise HTTPException(status_code=400, detail="Domain contains invalid characters")
    
    return domain

# Replace line 785-786 with:
domain = validate_domain(request.domain)

# Replace all subprocess.Popen with shell=True to use shell=False with argument lists
# Example - line 1097-1098 change from:
subprocess.Popen(f'start "Caddy Server" "{caddy_exe}" run --config "{caddyfile_path}"', shell=True, ...)
# To:
subprocess.Popen(["cmd", "/c", "start", "Caddy Server", caddy_exe, "run", "--config", caddyfile_path], shell=False, ...)
```

**Verification:** Write test with malicious domain input: `test"; rm -rf /; echo "`

---

### 1.2 GUARDIAN-002: Hardcoded Sentry DSN [BLOCKER]

**File:** `backend/app/main.py:34-35`

**Task:** Move Sentry DSN to environment variable.

```python
# Change from:
sentry_sdk.init(
    dsn="https://25adcc072579ef98fbb6b54096aca34f@o4510598139478016.ingest.us.sentry.io/4510598147473408",
    ...
)

# To:
sentry_dsn = os.getenv("SENTRY_DSN")
if SENTRY_AVAILABLE and sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        environment=getattr(settings, "ENVIRONMENT", "development"),
    )
```

**File:** `backend/.env.example`

**Task:** Add SENTRY_DSN placeholder.

```ini
# Sentry Error Tracking (optional)
# SENTRY_DSN=https://your-key@your-org.ingest.sentry.io/your-project
```

**Post-fix:** Rotate the Sentry DSN key in Sentry dashboard (old key is in git history).

---

### 1.3 GUARDIAN-004: SECRET_KEY Bypass [HIGH but Security-Critical]

**File:** `backend/app/core/security.py:18`

**Task:** Use settings.SECRET_KEY instead of direct os.environ access.

```python
# Change from:
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-in-production")

# To:
from app.core.settings import settings
SECRET_KEY = settings.SECRET_KEY
```

This ensures the production validator in settings.py actually protects JWT signing.

---

### 1.4 OPERATOR-001: No Rollback Procedure [BLOCKER]

**File:** Create `docs/ROLLBACK.md`

```markdown
# FilaOps Rollback Procedures

## Quick Reference

| Scenario | Command |
|----------|---------|
| Rollback last migration | `alembic downgrade -1` |
| Rollback to specific revision | `alembic downgrade <revision>` |
| Docker rollback | `docker-compose down && git checkout <tag> && docker-compose up --build` |

## 1. Application-Only Rollback (No Migration Changes)

If the deployment failed but no database migrations were involved:

```bash
# Docker deployment
docker-compose down
git checkout v3.0.0  # Previous known-good tag
docker-compose up --build -d

# Manual deployment
git checkout v3.0.0
cd backend && pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 2. Migration Rollback

If a migration failed or caused issues:

```bash
# Check current revision
alembic current

# View migration history
alembic history

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade abc123def456

# Verify rollback
alembic current
```

**IMPORTANT:** Always backup the database before running migrations:
```bash
pg_dump -h localhost -U filaops filaops > backup_$(date +%Y%m%d_%H%M%S).sql
```

## 3. Emergency Database Restore

If data corruption occurred:

```bash
# Stop all services
docker-compose down

# Restore from backup
psql -h localhost -U filaops filaops < backup_20260131_120000.sql

# Restart services
docker-compose up -d
```

## 4. Docker Compose Full Rollback

```bash
# Stop current deployment
docker-compose down

# Remove volumes if data is corrupted (DESTRUCTIVE)
docker-compose down -v

# Checkout previous version
git checkout v3.0.0

# Rebuild and start
docker-compose up --build -d

# Verify health
curl http://localhost:8000/health
```

## 5. Handling Coupled Migration + Server Start

The current Dockerfile runs `alembic upgrade head && uvicorn`. If migration fails:

1. Check logs: `docker-compose logs backend`
2. Enter container: `docker-compose run backend bash`
3. Manually rollback: `alembic downgrade -1`
4. Exit and restart: `docker-compose up -d`

## Pre-Deployment Checklist

- [ ] Database backup taken
- [ ] Previous version tag noted
- [ ] Rollback tested in staging
- [ ] Team notified of deployment window
```

---

### 1.5 SENTINEL-001 & SENTINEL-002: Auth & Payment Test Coverage [BLOCKER]

**Task:** Create comprehensive test suites for auth and payment endpoints.

**File:** Create `backend/tests/api/test_auth.py`

```python
"""
Authentication endpoint tests.
Target: 100% coverage of backend/app/api/v1/endpoints/auth.py
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.models.user import User

client = TestClient(app)


class TestLogin:
    """Tests for POST /api/v1/auth/login"""
    
    def test_login_success(self, db_session, test_user):
        response = client.post("/api/v1/auth/login", json={
            "email": test_user.email,
            "password": "testpassword123"
        })
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "refresh_token" in response.json()
    
    def test_login_invalid_email(self, db_session):
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "password"
        })
        assert response.status_code == 401
    
    def test_login_invalid_password(self, db_session, test_user):
        response = client.post("/api/v1/auth/login", json={
            "email": test_user.email,
            "password": "wrongpassword"
        })
        assert response.status_code == 401
    
    def test_login_rate_limit(self, db_session, test_user):
        """Test that login is rate limited to 5/minute"""
        for i in range(6):
            response = client.post("/api/v1/auth/login", json={
                "email": test_user.email,
                "password": "wrongpassword"
            })
        assert response.status_code == 429


class TestRegister:
    """Tests for POST /api/v1/auth/register"""
    
    def test_register_success(self, db_session):
        response = client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "name": "New User"
        })
        assert response.status_code == 201
    
    def test_register_duplicate_email(self, db_session, test_user):
        response = client.post("/api/v1/auth/register", json={
            "email": test_user.email,
            "password": "SecurePass123!",
            "name": "Duplicate User"
        })
        assert response.status_code == 400
    
    def test_register_weak_password(self, db_session):
        response = client.post("/api/v1/auth/register", json={
            "email": "weak@example.com",
            "password": "123",
            "name": "Weak Password User"
        })
        assert response.status_code == 422


class TestRefreshToken:
    """Tests for POST /api/v1/auth/refresh"""
    
    def test_refresh_success(self, db_session, test_user, auth_tokens):
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": auth_tokens["refresh_token"]
        })
        assert response.status_code == 200
        assert "access_token" in response.json()
    
    def test_refresh_invalid_token(self, db_session):
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid-token"
        })
        assert response.status_code == 401
    
    def test_refresh_expired_token(self, db_session, expired_refresh_token):
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": expired_refresh_token
        })
        assert response.status_code == 401


class TestPasswordReset:
    """Tests for password reset flow"""
    
    def test_request_password_reset(self, db_session, test_user):
        response = client.post("/api/v1/auth/password-reset/request", json={
            "email": test_user.email
        })
        assert response.status_code == 200
    
    def test_request_password_reset_nonexistent_email(self, db_session):
        # Should still return 200 to prevent email enumeration
        response = client.post("/api/v1/auth/password-reset/request", json={
            "email": "nonexistent@example.com"
        })
        assert response.status_code == 200
    
    def test_complete_password_reset(self, db_session, test_user, reset_token):
        response = client.post("/api/v1/auth/password-reset/complete", json={
            "token": reset_token,
            "new_password": "NewSecurePass123!"
        })
        assert response.status_code == 200
    
    def test_complete_password_reset_invalid_token(self, db_session):
        response = client.post("/api/v1/auth/password-reset/complete", json={
            "token": "invalid-token",
            "new_password": "NewSecurePass123!"
        })
        assert response.status_code == 400


class TestLogout:
    """Tests for POST /api/v1/auth/logout"""
    
    def test_logout_success(self, db_session, auth_headers):
        response = client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 200
    
    def test_logout_no_auth(self, db_session):
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 401


class TestCurrentUser:
    """Tests for GET /api/v1/auth/me"""
    
    def test_get_current_user(self, db_session, test_user, auth_headers):
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["email"] == test_user.email
    
    def test_get_current_user_no_auth(self, db_session):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
```

**File:** Create `backend/tests/api/test_payments.py`

```python
"""
Payment endpoint tests.
Target: 100% coverage of backend/app/api/v1/endpoints/payments.py
"""
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestCreatePayment:
    """Tests for POST /api/v1/payments"""
    
    def test_create_payment_success(self, db_session, auth_headers, test_sales_order):
        response = client.post("/api/v1/payments", 
            headers=auth_headers,
            json={
                "sales_order_id": test_sales_order.id,
                "amount": "100.00",
                "payment_method": "credit_card",
                "reference": "TXN-123456"
            }
        )
        assert response.status_code == 201
        assert response.json()["amount"] == "100.00"
    
    def test_create_payment_invalid_amount(self, db_session, auth_headers, test_sales_order):
        response = client.post("/api/v1/payments",
            headers=auth_headers,
            json={
                "sales_order_id": test_sales_order.id,
                "amount": "-50.00",
                "payment_method": "credit_card"
            }
        )
        assert response.status_code == 422
    
    def test_create_payment_exceeds_balance(self, db_session, auth_headers, test_sales_order):
        # Order total is $100, try to pay $200
        response = client.post("/api/v1/payments",
            headers=auth_headers,
            json={
                "sales_order_id": test_sales_order.id,
                "amount": "200.00",
                "payment_method": "credit_card"
            }
        )
        assert response.status_code == 400
    
    def test_create_payment_nonexistent_order(self, db_session, auth_headers):
        response = client.post("/api/v1/payments",
            headers=auth_headers,
            json={
                "sales_order_id": 99999,
                "amount": "100.00",
                "payment_method": "credit_card"
            }
        )
        assert response.status_code == 404


class TestRefundPayment:
    """Tests for POST /api/v1/payments/{id}/refund"""
    
    def test_refund_full_payment(self, db_session, auth_headers, test_payment):
        response = client.post(f"/api/v1/payments/{test_payment.id}/refund",
            headers=auth_headers,
            json={"amount": str(test_payment.amount), "reason": "Customer request"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "refunded"
    
    def test_refund_partial_payment(self, db_session, auth_headers, test_payment):
        partial_amount = test_payment.amount / 2
        response = client.post(f"/api/v1/payments/{test_payment.id}/refund",
            headers=auth_headers,
            json={"amount": str(partial_amount), "reason": "Partial refund"}
        )
        assert response.status_code == 200
    
    def test_refund_exceeds_original(self, db_session, auth_headers, test_payment):
        response = client.post(f"/api/v1/payments/{test_payment.id}/refund",
            headers=auth_headers,
            json={"amount": "99999.00", "reason": "Too much"}
        )
        assert response.status_code == 400
    
    def test_refund_already_refunded(self, db_session, auth_headers, refunded_payment):
        response = client.post(f"/api/v1/payments/{refunded_payment.id}/refund",
            headers=auth_headers,
            json={"amount": "10.00", "reason": "Double refund attempt"}
        )
        assert response.status_code == 400


class TestVoidPayment:
    """Tests for POST /api/v1/payments/{id}/void"""
    
    def test_void_payment_success(self, db_session, auth_headers, test_payment):
        response = client.post(f"/api/v1/payments/{test_payment.id}/void",
            headers=auth_headers,
            json={"reason": "Duplicate payment"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "voided"
    
    def test_void_already_voided(self, db_session, auth_headers, voided_payment):
        response = client.post(f"/api/v1/payments/{voided_payment.id}/void",
            headers=auth_headers,
            json={"reason": "Try again"}
        )
        assert response.status_code == 400


class TestPaymentDashboard:
    """Tests for GET /api/v1/payments/dashboard"""
    
    def test_dashboard_stats(self, db_session, auth_headers, multiple_payments):
        response = client.get("/api/v1/payments/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_collected" in data
        assert "total_refunded" in data
        assert "payment_count" in data
    
    def test_dashboard_date_filter(self, db_session, auth_headers, multiple_payments):
        response = client.get("/api/v1/payments/dashboard",
            headers=auth_headers,
            params={"start_date": "2026-01-01", "end_date": "2026-01-31"}
        )
        assert response.status_code == 200


class TestListPayments:
    """Tests for GET /api/v1/payments"""
    
    def test_list_payments(self, db_session, auth_headers, multiple_payments):
        response = client.get("/api/v1/payments", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1
    
    def test_list_payments_pagination(self, db_session, auth_headers, multiple_payments):
        response = client.get("/api/v1/payments",
            headers=auth_headers,
            params={"skip": 0, "limit": 5}
        )
        assert response.status_code == 200
        assert len(response.json()) <= 5
    
    def test_list_payments_filter_by_order(self, db_session, auth_headers, test_sales_order, multiple_payments):
        response = client.get("/api/v1/payments",
            headers=auth_headers,
            params={"sales_order_id": test_sales_order.id}
        )
        assert response.status_code == 200
```

---

## Phase 2: High Priority Fixes

### 2.1 OPERATOR-002: Health Check Must Verify DB

**File:** `backend/app/main.py:270-272`

```python
# Replace the shallow health check with:
@app.get("/health")
async def health_check():
    """Deep health check that verifies critical dependencies."""
    checks = {}
    overall_healthy = True
    
    # Check database connectivity
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"failed: {str(e)}"
        overall_healthy = False
    
    # Check disk space (warn if <10% free)
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        free_percent = (free / total) * 100
        if free_percent < 10:
            checks["disk"] = f"warning: {free_percent:.1f}% free"
        else:
            checks["disk"] = "ok"
    except Exception:
        checks["disk"] = "unknown"
    
    status_code = 200 if overall_healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if overall_healthy else "unhealthy",
            "checks": checks,
            "version": settings.VERSION
        }
    )
```

**File:** `docker-compose.yml` - Add healthcheck to backend service:

```yaml
backend:
  # ... existing config ...
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
```

---

### 2.2 OPERATOR-003: Frontend Docker - Dev Server in Production

**File:** `frontend/Dockerfile`

**Task:** First, fix the useCallback temporal dead zone issues blocking production builds, then update Dockerfile.

**Files to fix (useCallback issues):** Run this to find them:
```bash
grep -r "useCallback" frontend/src --include="*.jsx" -l | head -30
```

Common fix pattern:
```javascript
// BEFORE (temporal dead zone - function used before defined):
const MyComponent = () => {
  useEffect(() => {
    fetchData();  // ERROR: fetchData not yet defined
  }, [fetchData]);
  
  const fetchData = useCallback(() => { ... }, []);
};

// AFTER (define before use):
const MyComponent = () => {
  const fetchData = useCallback(() => { ... }, []);
  
  useEffect(() => {
    fetchData();
  }, [fetchData]);
};
```

**After fixing useCallback issues, update Dockerfile:**

```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**File:** Create `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

### 2.3 OPERATOR-004: Decouple Migration from Server Start

**File:** `backend/Dockerfile:30`

```dockerfile
# Change from:
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

# To:
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**File:** `docker-compose.yml` - Add migration service:

```yaml
services:
  migrate:
    build: ./backend
    command: alembic upgrade head
    environment:
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      db:
        condition: service_healthy
    restart: "no"
  
  backend:
    # ... existing config ...
    depends_on:
      migrate:
        condition: service_completed_successfully
      db:
        condition: service_healthy
```

---

### 2.4 GUARDIAN-003: Seed Data Endpoint Auth

**File:** `backend/app/api/v1/endpoints/setup.py:143-146`

```python
# Change from:
@router.post("/seed-example-data", response_model=SeedDataResponse)
def seed_example_data(
    db: Session = Depends(get_db)
):

# To:
@router.post("/seed-example-data", response_model=SeedDataResponse)
def seed_example_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    # Also add guard for fresh database only
    user_count = db.query(User).count()
    if user_count > 1:
        raise HTTPException(
            status_code=400, 
            detail="Seeding only allowed on fresh installations"
        )
```

**Also remove tracebacks from error responses (lines 171-174, 180-184, 204-206):**

```python
# Change from:
error_trace = traceback.format_exc()
raise HTTPException(
    status_code=500,
    detail=f"Failed to seed example items: {str(e)}\n\nTraceback:\n{error_trace}"
)

# To:
logger.error("Failed to seed example items", exc_info=True)
raise HTTPException(
    status_code=500,
    detail="Failed to seed example data. Check server logs for details."
)
```

---

### 2.5 GUARDIAN-005: Remove Reset Token from Logs

**File:** `backend/app/api/v1/endpoints/auth.py:499-507`

```python
# Change from:
logger.info(
    "Password reset auto-approved (email not configured)",
    extra={
        "user_id": user.id,
        "email": user.email,
        "request_id": reset_request.id,
        "reset_token": reset_token  # REMOVE THIS
    }
)

# To:
logger.info(
    "Password reset auto-approved (email not configured)",
    extra={
        "user_id": user.id,
        "email": user.email,
        "request_id": reset_request.id,
        "token_prefix": reset_token[:8] + "..."  # Safe truncated version
    }
)
```

---

### 2.6 GUARDIAN-006: Gate Process Execution Endpoints

**File:** `backend/app/api/v1/endpoints/security.py`

Add to each process execution endpoint (lines 354, 488, etc.):

```python
@router.post("/remediate/open-env-file")
async def open_env_file(...):
    # Add at start of function:
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=403,
            detail="This endpoint is disabled in production environments"
        )
    
    if not getattr(settings, "ENABLE_LOCAL_REMEDIATION", False):
        raise HTTPException(
            status_code=403,
            detail="Local remediation endpoints are disabled. Set ENABLE_LOCAL_REMEDIATION=true to enable."
        )
    # ... rest of function
```

**File:** `backend/.env.example`

```ini
# Local development helpers (NEVER enable in production)
# ENABLE_LOCAL_REMEDIATION=true
```

---

### 2.7 SENTINEL-005: Fix MRP Test Failures

**File:** `backend/tests/services/test_mrp_service.py`

**Task:** Debug and fix these 4 failing tests:
- `test_release_purchase_creates_po`
- `test_release_firmed_order_succeeds`
- `test_processes_production_orders`
- `test_draft_production_orders_included`

Common issues to check:
1. Fixture data not matching expected state
2. Database session not rolling back between tests
3. Mock objects not configured correctly
4. Date/time dependencies (use `freezegun`)

```python
# Add to conftest.py if not present:
@pytest.fixture(autouse=True)
def db_session(db):
    """Ensure clean rollback after each test."""
    yield db
    db.rollback()
```

---

### 2.8 SENTINEL-006: Fix 1599 Test Errors

**Task:** This is likely a cascading fixture issue. Debug approach:

```bash
# Run single test file to isolate
pytest tests/api/test_items.py -v

# Run with verbose fixture info
pytest tests/ -v --setup-show 2>&1 | head -100

# Check for missing fixture
pytest tests/ --collect-only 2>&1 | grep -i error
```

**Common fix:** Add missing `db` fixture cleanup:

**File:** `backend/tests/conftest.py`

```python
@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()
```

---

## Phase 3: Architecture & Code Quality (ARCHITECT findings)

### 3.1 ARCHITECT-001 & 005: Fix N+1 Queries

**File:** `backend/app/api/v1/endpoints/admin/dashboard.py:386-516`

```python
# Replace N+1 pattern with batch queries:

# BEFORE:
active_orders = db.query(SalesOrder).filter(...).all()
for order in active_orders:
    lines = db.query(SalesOrderLine).filter(
        SalesOrderLine.sales_order_id == order.id
    ).all()

# AFTER:
from sqlalchemy.orm import selectinload

active_orders = db.query(SalesOrder).options(
    selectinload(SalesOrder.lines).selectinload(SalesOrderLine.product)
).filter(...).limit(100).all()  # Add limit!
```

**File:** `backend/app/api/v1/endpoints/admin/bom.py:203-204`

```python
# BEFORE:
for line in bom.lines:
    component = db.query(Product).filter(Product.id == line.component_id).first()

# AFTER:
component_ids = [line.component_id for line in bom.lines]
components = db.query(Product).filter(Product.id.in_(component_ids)).all()
component_map = {c.id: c for c in components}

for line in bom.lines:
    component = component_map.get(line.component_id)
```

---

### 3.2 ARCHITECT-003: Create get_or_404 Utility

**File:** Create `backend/app/core/utils.py`

```python
from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import TypeVar, Type

T = TypeVar('T')

def get_or_404(db: Session, model: Type[T], id: int, detail: str = None) -> T:
    """Get an entity by ID or raise 404."""
    entity = db.query(model).filter(model.id == id).first()
    if not entity:
        detail = detail or f"{model.__name__} not found"
        raise HTTPException(status_code=404, detail=detail)
    return entity
```

**Usage across codebase:**

```python
# BEFORE (repeated 187+ times):
item = db.query(Product).filter(Product.id == item_id).first()
if not item:
    raise HTTPException(status_code=404, detail="Item not found")

# AFTER:
from app.core.utils import get_or_404
item = get_or_404(db, Product, item_id)
```

---

### 3.3 ARCHITECT-004: Create Shared React Hooks

**File:** Create `frontend/src/hooks/useApi.js`

```javascript
import { useState, useCallback } from 'react';
import { createApiClient } from '../lib/apiClient';

export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const api = createApiClient();
  
  const request = useCallback(async (method, endpoint, data = null) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api[method](endpoint, data);
      return response;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [api]);
  
  return {
    loading,
    error,
    get: (endpoint) => request('get', endpoint),
    post: (endpoint, data) => request('post', endpoint, data),
    put: (endpoint, data) => request('put', endpoint, data),
    delete: (endpoint) => request('delete', endpoint),
  };
}
```

**File:** Create `frontend/src/hooks/useCRUD.js`

```javascript
import { useState, useEffect, useCallback } from 'react';
import { useApi } from './useApi';

export function useCRUD(endpoint) {
  const [items, setItems] = useState([]);
  const { loading, error, get, post, put, delete: del } = useApi();
  
  const fetchAll = useCallback(async () => {
    const data = await get(endpoint);
    setItems(Array.isArray(data) ? data : []);
  }, [endpoint, get]);
  
  const create = useCallback(async (data) => {
    const newItem = await post(endpoint, data);
    setItems(prev => [...prev, newItem]);
    return newItem;
  }, [endpoint, post]);
  
  const update = useCallback(async (id, data) => {
    const updated = await put(`${endpoint}/${id}`, data);
    setItems(prev => prev.map(item => item.id === id ? updated : item));
    return updated;
  }, [endpoint, put]);
  
  const remove = useCallback(async (id) => {
    await del(`${endpoint}/${id}`);
    setItems(prev => prev.filter(item => item.id !== id));
  }, [endpoint, del]);
  
  useEffect(() => {
    fetchAll();
  }, [fetchAll]);
  
  return { items, loading, error, fetchAll, create, update, remove };
}
```

---

### 3.4 ARCHITECT-008: Remove console.log Statements

**Task:** Remove all 14 console.log statements from production code.

```bash
# Find them:
grep -rn "console.log" frontend/src/pages frontend/src/components --include="*.jsx" | grep -v node_modules

# Files to clean:
# - AdminBOM.jsx:791, 797, 3617
# - AdminPurchasing.jsx:307, 314, 320, 523
# - RecordPaymentModal.jsx:177
# - ScrapOrderModal.jsx:27, 31, 35, 37
# - OrderDetail.jsx:777
```

Replace with conditional debug logging:

```javascript
// Create frontend/src/lib/debug.js
const DEBUG = import.meta.env.DEV;

export function debugLog(...args) {
  if (DEBUG) {
    console.log('[DEBUG]', ...args);
  }
}

// Usage:
import { debugLog } from '../lib/debug';
debugLog("BOM Line data sample:", data.lines[0]);
```

---

## Phase 4: UX Fixes (NAVIGATOR findings)

### 4.1 NAVIGATOR-001: Add 404 Route

**File:** `frontend/src/App.jsx`

```jsx
import NotFound from './pages/NotFound';

// Inside <Routes>:
<Routes>
  {/* ... existing routes ... */}
  
  {/* Catch-all 404 - must be last */}
  <Route path="*" element={<NotFound />} />
</Routes>
```

**File:** Create `frontend/src/pages/NotFound.jsx`

```jsx
import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-gray-400 mb-4">404</h1>
        <p className="text-xl text-gray-500 mb-8">Page not found</p>
        <Link 
          to="/admin" 
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
}
```

---

### 4.2 NAVIGATOR-002: Create Accessible Modal Component

**File:** Create `frontend/src/components/ui/Modal.jsx`

```jsx
import { useEffect, useRef } from 'react';

export default function Modal({ 
  isOpen, 
  onClose, 
  title, 
  children,
  size = 'md' // sm, md, lg, xl
}) {
  const modalRef = useRef(null);
  const previousActiveElement = useRef(null);
  
  // Handle Escape key
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);
  
  // Focus trap and restore
  useEffect(() => {
    if (isOpen) {
      previousActiveElement.current = document.activeElement;
      modalRef.current?.focus();
    } else if (previousActiveElement.current) {
      previousActiveElement.current.focus();
    }
  }, [isOpen]);
  
  if (!isOpen) return null;
  
  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
  };
  
  return (
    <div 
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        tabIndex={-1}
        className={`bg-gray-900 rounded-lg p-6 w-full ${sizeClasses[size]} mx-4`}
      >
        <div className="flex justify-between items-center mb-4">
          <h2 id="modal-title" className="text-lg font-semibold text-white">
            {title}
          </h2>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="text-gray-400 hover:text-white"
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
```

---

### 4.3 NAVIGATOR-003: Add Back Button to Onboarding

**File:** `frontend/src/pages/Onboarding.jsx`

Add Back button to each step (2-6):

```jsx
// Add this component inside Onboarding.jsx:
const StepNavigation = ({ currentStep, setCurrentStep, canGoBack = true, loading = false }) => (
  <div className="flex justify-between mt-6">
    {canGoBack && currentStep > 1 ? (
      <button
        onClick={() => setCurrentStep(currentStep - 1)}
        disabled={loading}
        className="px-4 py-2 text-gray-400 hover:text-white disabled:opacity-50"
      >
        ← Back
      </button>
    ) : (
      <div />
    )}
    {/* Forward button is handled by each step's submit action */}
  </div>
);

// Use in each step's JSX, e.g. Step 2:
<StepNavigation 
  currentStep={currentStep} 
  setCurrentStep={setCurrentStep}
  loading={isSeeding}
/>
```

---

## Phase 5: Documentation Fixes (HERALD findings)

### 5.1 HERALD-001: Frontend README

**File:** Replace `frontend/README.md`

```markdown
# FilaOps Frontend

React-based admin dashboard for FilaOps ERP.

## Tech Stack

- **React 18** with Vite
- **Tailwind CSS** with custom neo-industrial dark theme
- **React Router** for navigation
- **Recharts** for data visualization

## Quick Start

```bash
npm install
npm run dev
```

Open http://localhost:5173

## Project Structure

```
src/
├── components/     # Reusable UI components
├── hooks/          # Custom React hooks
├── lib/            # Utilities and API client
├── pages/          # Route components
│   └── admin/      # Admin dashboard pages
└── services/       # API service functions
```

## Environment Variables

Create `.env.local`:

```ini
VITE_API_URL=http://localhost:8000
```

## Building

```bash
npm run build        # Development build (works)
npm run build:prod   # Production build (see PRODUCTION_BUILD_BLOCKED.md)
```

## Known Issues

See [PRODUCTION_BUILD_BLOCKED.md](./PRODUCTION_BUILD_BLOCKED.md) for build limitations.
```

---

### 5.2 HERALD-002: Create Email Configuration Docs

**File:** Create `docs/EMAIL_CONFIGURATION.md`

```markdown
# Email Configuration

FilaOps can send transactional emails for password resets and notifications.

## Environment Variables

Add to your `.env` file:

```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@yourcompany.com
SMTP_TLS=true
```

## Gmail Setup

1. Enable 2-Factor Authentication on your Google account
2. Generate an App Password: https://myaccount.google.com/apppasswords
3. Use the App Password (not your regular password) for SMTP_PASSWORD

## Testing

```bash
# Send test email via API
curl -X POST http://localhost:8000/api/v1/admin/test-email \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"to": "test@example.com"}'
```

## Disabling Email

If SMTP is not configured, FilaOps will:
- Auto-approve password reset requests (development mode)
- Log email content to console instead of sending
```

---

### 5.3 HERALD-003: Fix Project Name

**File:** `KNOWN_ISSUES.md:1`

```markdown
# FilaOps - Known Issues
```

---

### 5.4 HERALD-004: Create CHANGELOG

**File:** Create `CHANGELOG.md`

```markdown
# Changelog

All notable changes to FilaOps will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.1] - 2026-01-28

### Fixed
- UOM conversion calculation errors causing incorrect cost estimates
- MRP calculation edge cases with zero-quantity components

### Changed
- Improved error messages for inventory operations

## [3.0.0] - 2026-01-15

### Breaking Changes
- **PostgreSQL only** - Dropped SQL Server support
- Database schema changes require fresh migration

### Added
- Multi-location inventory tracking
- Spool-level filament management
- Production operation routing
- Accounting module with Schedule C mapping

### Changed
- Complete rewrite of MRP engine
- New admin dashboard design

### Removed
- SQL Server compatibility layer
- Legacy CSV import formats
```

---

## Phase 6: Test Coverage Push to 80%+

### 6.1 Coverage Gaps to Fill

| Module | Current | Target | Files to Test |
|--------|---------|--------|---------------|
| Auth | 0% | 90% | `auth.py` |
| Payments | 0% | 90% | `payments.py` |
| Services | 25% | 80% | 24 untested files |
| API Endpoints | 44% | 80% | 25 untested modules |
| Frontend | 0% unit | 60% | Add Vitest |

### 6.2 Test File Template

Use this template for each untested endpoint file:

```python
"""
Tests for backend/app/api/v1/endpoints/{module}.py
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestCreate{Entity}:
    def test_create_success(self, db_session, auth_headers, test_data):
        response = client.post("/api/v1/{endpoint}",
            headers=auth_headers,
            json={...}
        )
        assert response.status_code == 201
    
    def test_create_validation_error(self, db_session, auth_headers):
        response = client.post("/api/v1/{endpoint}",
            headers=auth_headers,
            json={"invalid": "data"}
        )
        assert response.status_code == 422
    
    def test_create_unauthorized(self, db_session):
        response = client.post("/api/v1/{endpoint}", json={...})
        assert response.status_code == 401


class TestGet{Entity}:
    def test_get_by_id(self, db_session, auth_headers, test_entity):
        response = client.get(f"/api/v1/{endpoint}/{test_entity.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_get_not_found(self, db_session, auth_headers):
        response = client.get("/api/v1/{endpoint}/99999",
            headers=auth_headers
        )
        assert response.status_code == 404


class TestUpdate{Entity}:
    def test_update_success(self, db_session, auth_headers, test_entity):
        response = client.put(f"/api/v1/{endpoint}/{test_entity.id}",
            headers=auth_headers,
            json={...}
        )
        assert response.status_code == 200


class TestDelete{Entity}:
    def test_delete_success(self, db_session, auth_headers, test_entity):
        response = client.delete(f"/api/v1/{endpoint}/{test_entity.id}",
            headers=auth_headers
        )
        assert response.status_code == 200


class TestList{Entity}:
    def test_list_all(self, db_session, auth_headers, multiple_entities):
        response = client.get("/api/v1/{endpoint}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1
    
    def test_list_pagination(self, db_session, auth_headers, multiple_entities):
        response = client.get("/api/v1/{endpoint}",
            headers=auth_headers,
            params={"skip": 0, "limit": 5}
        )
        assert len(response.json()) <= 5
```

### 6.3 Frontend Testing Setup

**File:** `frontend/package.json` - Add test dependencies:

```json
{
  "devDependencies": {
    "@testing-library/react": "^14.0.0",
    "@testing-library/jest-dom": "^6.0.0",
    "@testing-library/user-event": "^14.0.0",
    "vitest": "^1.0.0",
    "jsdom": "^23.0.0"
  },
  "scripts": {
    "test": "vitest",
    "test:coverage": "vitest --coverage"
  }
}
```

**File:** Create `frontend/vitest.config.js`:

```javascript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
    coverage: {
      reporter: ['text', 'html'],
      exclude: ['node_modules/', 'src/test/'],
    },
  },
});
```

**File:** Create `frontend/src/test/setup.js`:

```javascript
import '@testing-library/jest-dom';
```

---

## Verification Checklist

After completing all phases, verify:

- [ ] `pytest tests/ -v` - All tests pass
- [ ] `pytest tests/ --cov=app --cov-report=term-missing` - Coverage >80%
- [ ] `npm test` in frontend - All tests pass
- [ ] `docker-compose up --build` - Builds and starts successfully
- [ ] `curl http://localhost:8000/health` - Returns healthy with DB check
- [ ] No console.log in production build
- [ ] All blockers resolved

---

## Quick Reference: All 71 Findings

### SENTINEL (10)
- [x] SENTINEL-001: Auth 0% coverage [BLOCKER]
- [x] SENTINEL-002: Payments 0% coverage [BLOCKER]
- [ ] SENTINEL-003: 75% services untested [HIGH]
- [ ] SENTINEL-004: 56% endpoints untested [HIGH]
- [ ] SENTINEL-005: 4 MRP tests failing [HIGH]
- [ ] SENTINEL-006: 1599 test errors [MEDIUM]
- [ ] SENTINEL-007: Frontend 0 unit tests [MEDIUM]
- [ ] SENTINEL-008: Integration tests skip payments [MEDIUM]
- [ ] SENTINEL-009: Inconsistent fixture rollback [LOW]
- [ ] SENTINEL-010: SQLAlchemy deprecated API [LOW]

### GUARDIAN (12)
- [x] GUARDIAN-001: Command injection [BLOCKER] (fixed: validate_domain + shell=False)
- [x] GUARDIAN-002: Hardcoded Sentry DSN [BLOCKER]
- [x] GUARDIAN-003: Seed endpoint no auth [HIGH]
- [x] GUARDIAN-004: SECRET_KEY bypass [HIGH]
- [x] GUARDIAN-005: Reset token in logs [HIGH]
- [x] GUARDIAN-006: Process execution endpoints [HIGH]
- [ ] GUARDIAN-007: CORS wildcard fallback [MEDIUM]
- [ ] GUARDIAN-008: Debug config endpoint [MEDIUM]
- [ ] GUARDIAN-009: Traceback in errors [MEDIUM]
- [ ] GUARDIAN-010: SQL injection in scripts [MEDIUM]
- [ ] GUARDIAN-011: Refresh no rate limit [LOW]
- [ ] GUARDIAN-012: Reset via GET [LOW]

### ARCHITECT (14)
- [ ] ARCHITECT-001: N+1 dashboard queries [HIGH]
- [ ] ARCHITECT-002: God files [HIGH]
- [ ] ARCHITECT-003: Endpoints bypass services [HIGH]
- [ ] ARCHITECT-004: Frontend duplication [HIGH]
- [ ] ARCHITECT-005: N+1 BOM queries [HIGH]
- [ ] ARCHITECT-006: Raw dicts not Pydantic [MEDIUM]
- [ ] ARCHITECT-007: 34 TODOs/deprecated [MEDIUM]
- [ ] ARCHITECT-008: console.log in prod [MEDIUM]
- [ ] ARCHITECT-009: Query monitor incomplete [MEDIUM]
- [ ] ARCHITECT-010: Promise.all no catch [MEDIUM]
- [ ] ARCHITECT-011: Inconsistent response format [MEDIUM]
- [ ] ARCHITECT-012: URL naming inconsistent [LOW]
- [ ] ARCHITECT-013: Deprecated Machine model [LOW]
- [ ] ARCHITECT-014: Raw fetch vs apiClient [LOW]

### NAVIGATOR (14)
- [ ] NAVIGATOR-001: No 404 route [HIGH]
- [ ] NAVIGATOR-002: Modals no ARIA [HIGH]
- [ ] NAVIGATOR-003: Onboarding no back [HIGH]
- [ ] NAVIGATOR-004: Inventory import missing [HIGH]
- [ ] NAVIGATOR-005: Labels not associated [MEDIUM]
- [ ] NAVIGATOR-006: Hardcoded vs CSS vars [MEDIUM]
- [ ] NAVIGATOR-007: Technical error toasts [MEDIUM]
- [ ] NAVIGATOR-008: Onboarding style mismatch [MEDIUM]
- [ ] NAVIGATOR-009: EmptyState low contrast [MEDIUM]
- [ ] NAVIGATOR-010: No chart loading state [MEDIUM]
- [ ] NAVIGATOR-011: ConfirmDialog focus [LOW]
- [ ] NAVIGATOR-012: Hamburger no label [LOW]
- [ ] NAVIGATOR-013: Empty login link [LOW]
- [ ] NAVIGATOR-014: ForgotPassword brand [LOW]

### HERALD (10)
- [ ] HERALD-001: Frontend README boilerplate [HIGH]
- [ ] HERALD-002: Missing email docs [HIGH]
- [ ] HERALD-003: Wrong project name [HIGH]
- [ ] HERALD-004: No CHANGELOG [MEDIUM]
- [ ] HERALD-005: No CONTRIBUTING [MEDIUM]
- [ ] HERALD-006: README no prerequisites [MEDIUM]
- [ ] HERALD-007: Docker not in README [MEDIUM]
- [ ] HERALD-008: Only accounting guide [LOW]
- [ ] HERALD-009: Schema version stale [LOW]
- [ ] HERALD-010: No troubleshooting [LOW]

### OPERATOR (11)
- [x] OPERATOR-001: No rollback docs [BLOCKER]
- [x] OPERATOR-002: Shallow health check [HIGH]
- [x] OPERATOR-003: Frontend dev in prod [HIGH]
- [x] OPERATOR-004: Coupled migration/start [HIGH]
- [ ] OPERATOR-005: No correlation IDs [MEDIUM]
- [ ] OPERATOR-006: Version mismatch [MEDIUM]
- [ ] OPERATOR-007: CI postgres version [MEDIUM]
- [ ] OPERATOR-008: No CSP header [MEDIUM]
- [ ] OPERATOR-009: Docker runs as root [LOW]
- [ ] OPERATOR-010: Sentry DSN hardcoded [LOW]
- [ ] OPERATOR-011: CI SECRET_KEY bypass [LOW]

---

*Generated by Review Council - FilaOps v3.0.1*
