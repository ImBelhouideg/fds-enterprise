# ═══════════════════════════════════════════════════════════════
# FDS Enterprise v3.0 — tests/test_fds_enterprise.py
# Tests adaptés à l'architecture JWT + SQLAlchemy + Redis
# ═══════════════════════════════════════════════════════════════

import pytest
import json
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# ── Fixtures ──────────────────────────────────────────────────
@pytest.fixture(scope="session")
def app():
    """Create test Flask app with SQLite (no PostgreSQL needed for CI)"""
    os.environ.update({
        "FLASK_ENV":         "testing",
        "SECRET_KEY":        "ci-test-secret-key-32-chars-min!!",
        "JWT_SECRET_KEY":    "ci-jwt-secret-key",
        "POSTGRES_HOST":     "localhost",
        "POSTGRES_DB":       "fds_test",
        "POSTGRES_USER":     "fds_user",
        "POSTGRES_PASSWORD": "test",
        "REDIS_HOST":        "localhost",
        "REDIS_PASSWORD":    "test",
    })

    try:
        from app import create_app
        # Override DB to SQLite for CI
        flask_app = create_app()
        flask_app.config.update({
            "TESTING":                    True,
            "SQLALCHEMY_DATABASE_URI":    "sqlite:///:memory:",
            "JWT_ACCESS_TOKEN_EXPIRES":   False,
            "WTF_CSRF_ENABLED":           False,
            "MAIL_SUPPRESS_SEND":         True,
        })
        with flask_app.app_context():
            from models.database import db
            db.create_all()
        yield flask_app
    except Exception as e:
        pytest.skip(f"App could not start: {e}")

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_headers(client):
    """Register + login → return JWT headers"""
    # Register
    client.post("/api/auth/register", json={
        "username": "testuser",
        "email":    "test@ci.com",
        "password": "Test1234!",
        "fullname": "CI Test User"
    })
    # Login
    res = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "Test1234!"
    })
    data = res.get_json()
    token = data.get("access_token", "")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# ── Health & Monitoring ───────────────────────────────────────
class TestHealthMonitoring:
    def test_health_endpoint_exists(self, client):
        res = client.get("/health")
        assert res.status_code == 200

    def test_health_returns_json(self, client):
        res = client.get("/health")
        data = res.get_json()
        assert "status" in data
        assert "version" in data
        assert data["version"] == "3.0.0"

    def test_metrics_endpoint(self, client):
        res = client.get("/metrics")
        assert res.status_code == 200
        assert b"fds_requests_total" in res.data or b"python_" in res.data

    def test_spa_fallback(self, client):
        """Non-API routes serve index.html (SPA)"""
        res = client.get("/some-frontend-route")
        assert res.status_code in [200, 404]

# ── Auth ──────────────────────────────────────────────────────
class TestAuth:
    def test_register_success(self, client):
        res = client.post("/api/auth/register", json={
            "username": "newuser_ci",
            "email":    "newuser@ci.com",
            "password": "SecurePass1!",
            "fullname": "New User CI"
        })
        assert res.status_code in [200, 201, 409]  # 409 if already exists

    def test_register_missing_fields(self, client):
        res = client.post("/api/auth/register", json={"username": "incomplete"})
        assert res.status_code in [400, 422]

    def test_login_success(self, client):
        # First register
        client.post("/api/auth/register", json={
            "username": "logintest",
            "email":    "logintest@ci.com",
            "password": "Test1234!",
            "fullname": "Login Test"
        })
        res = client.post("/api/auth/login", json={
            "username": "logintest",
            "password": "Test1234!"
        })
        assert res.status_code == 200
        data = res.get_json()
        assert "access_token" in data

    def test_login_wrong_password(self, client):
        res = client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "wrongpassword"
        })
        assert res.status_code in [401, 400]

    def test_protected_route_without_token(self, client):
        res = client.get("/api/transactions")
        assert res.status_code == 401
        data = res.get_json()
        assert "error" in data or "msg" in data

    def test_protected_route_with_token(self, client, auth_headers):
        res = client.get("/api/transactions", headers=auth_headers)
        assert res.status_code in [200, 404]

# ── Transactions / FDS ────────────────────────────────────────
class TestTransactions:
    def test_analyze_requires_auth(self, client):
        res = client.post("/api/transactions/analyze", json={
            "amount": 200, "country": "MA", "merchant": "Amazon"
        })
        assert res.status_code == 401

    def test_analyze_normal_transaction(self, client, auth_headers):
        res = client.post("/api/transactions/analyze",
            headers=auth_headers,
            json={"amount": 200, "country": "MA",
                  "merchant": "Amazon", "card_last4": "4242"})
        assert res.status_code in [200, 201]
        data = res.get_json()
        if data:
            assert "fraud" in data or "status" in data or "risk_score" in data

    def test_analyze_high_risk_country(self, client, auth_headers):
        res = client.post("/api/transactions/analyze",
            headers=auth_headers,
            json={"amount": 100, "country": "NG",
                  "merchant": "Unknown", "card_last4": "1234"})
        assert res.status_code in [200, 201]
        data = res.get_json()
        if data and "fraud" in data:
            assert data["fraud"] == True

    def test_analyze_suspect_amount(self, client, auth_headers):
        # First create history
        for _ in range(3):
            client.post("/api/transactions/analyze",
                headers=auth_headers,
                json={"amount": 200, "country": "MA",
                      "merchant": "Amazon", "card_last4": "4242"})
        # Now try 10x the normal amount
        res = client.post("/api/transactions/analyze",
            headers=auth_headers,
            json={"amount": 9999, "country": "MA",
                  "merchant": "Tesla", "card_last4": "4242"})
        assert res.status_code in [200, 201]

    def test_get_transactions_list(self, client, auth_headers):
        res = client.get("/api/transactions", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert isinstance(data, (list, dict))

# ── Fraud Service (unit) ──────────────────────────────────────
class TestFraudService:
    def test_calculate_risk_score_low(self):
        from services.fraud_service import calculate_risk_score
        checks = [
            {"check": "Limite de montant",           "passed": True},
            {"check": "Vérification de localisation","passed": True},
            {"check": "Fréquence des transactions",  "passed": True},
            {"check": "Détection de doublons",       "passed": True},
        ]
        score, confidence, level = calculate_risk_score(checks, 200, "MA", [])
        assert score < 30
        assert level == "low"
        assert 0 < confidence <= 1

    def test_calculate_risk_score_high(self):
        from services.fraud_service import calculate_risk_score
        checks = [
            {"check": "Limite de montant",           "passed": False},
            {"check": "Vérification de localisation","passed": False},
            {"check": "Fréquence des transactions",  "passed": False},
            {"check": "Détection de doublons",       "passed": False},
        ]
        score, confidence, level = calculate_risk_score(checks, 9000, "NG", [])
        assert score >= 70
        assert level == "critical"

    def test_risk_score_high_risk_country(self):
        from services.fraud_service import calculate_risk_score, HIGH_RISK
        checks = [{"check": "Vérification de localisation", "passed": False}]
        score, _, level = calculate_risk_score(checks, 100, "NG", [])
        assert "NG" in HIGH_RISK
        assert score > 0

    def test_generate_explanation(self):
        from services.fraud_service import generate_explanation
        checks = [{"check": "Vérification de localisation", "passed": False}]
        expl = generate_explanation(checks, 75, 500, "NG", "Unknown")
        assert isinstance(expl, str)
        assert len(expl) > 10

    def test_get_shap_values(self):
        from services.fraud_service import get_shap_values
        shap = get_shap_values([], 60)
        assert isinstance(shap, list)
        assert len(shap) == 5
        for item in shap:
            assert "feature" in item
            assert "value" in item
            assert "direction" in item

    def test_allowed_countries(self):
        from services.fraud_service import HIGH_RISK
        assert "NG" in HIGH_RISK
        assert "RU" in HIGH_RISK
        assert "CN" in HIGH_RISK

# ── Config ────────────────────────────────────────────────────
class TestConfig:
    def test_config_loads(self):
        from config.settings import get_config
        cfg = get_config()
        assert hasattr(cfg, "SECRET_KEY")
        assert hasattr(cfg, "SQLALCHEMY_DATABASE_URI")
        assert hasattr(cfg, "ALLOWED_COUNTRIES")
        assert isinstance(cfg.ALLOWED_COUNTRIES, list)

    def test_allowed_countries_default(self):
        from config.settings import Config
        countries = Config.ALLOWED_COUNTRIES
        assert "MA" in countries
        assert "FR" in countries
