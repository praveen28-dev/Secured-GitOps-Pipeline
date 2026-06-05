"""
Container Security Falcon — Unit Tests

Tests cover:
  - Health and readiness probes
  - Order CRUD operations
  - Input validation and error handling
  - Security headers on all responses
  - Pipeline status endpoint
"""

import json

import pytest

from app import create_app


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app("testing")
    # Reset in-memory store for test isolation
    from app.routes import _orders
    _orders.clear()
    yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


# ═══════════════════════════════════════════════════════════════
#  HEALTH & READINESS PROBES
# ═══════════════════════════════════════════════════════════════


class TestHealthCheck:
    """Tests for the /health endpoint."""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        response = client.get("/health")
        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert data["service"] == "container-security-falcon"
        assert "uptime_seconds" in data
        assert "timestamp" in data

    def test_readiness_returns_200(self, client):
        response = client.get("/ready")
        assert response.status_code == 200

    def test_readiness_returns_checks(self, client):
        response = client.get("/ready")
        data = json.loads(response.data)
        assert data["status"] == "ready"
        assert "checks" in data


# ═══════════════════════════════════════════════════════════════
#  SECURITY HEADERS
# ═══════════════════════════════════════════════════════════════


class TestSecurityHeaders:
    """Verify security headers are present on all responses."""

    def test_x_content_type_options(self, client):
        response = client.get("/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        response = client.get("/health")
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_x_xss_protection(self, client):
        response = client.get("/health")
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_referrer_policy(self, client):
        response = client.get("/health")
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_content_security_policy(self, client):
        response = client.get("/health")
        assert response.headers.get("Content-Security-Policy") == "default-src 'self'"

    def test_strict_transport_security(self, client):
        response = client.get("/health")
        hsts = response.headers.get("Strict-Transport-Security")
        assert "max-age=31536000" in hsts

    def test_permissions_policy(self, client):
        response = client.get("/health")
        assert "geolocation=()" in response.headers.get("Permissions-Policy", "")

    def test_no_server_header(self, client):
        response = client.get("/health")
        # Server header should be removed to prevent fingerprinting
        assert "Server" not in response.headers or response.headers.get("Server") == ""


# ═══════════════════════════════════════════════════════════════
#  ORDER CRUD OPERATIONS
# ═══════════════════════════════════════════════════════════════


class TestOrderCreation:
    """Tests for POST /api/v1/orders."""

    def test_create_order_success(self, client):
        payload = {"item": "widget-a", "quantity": 5, "customer": "acme-corp"}
        response = client.post(
            "/api/v1/orders",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["order"]["item"] == "widget-a"
        assert data["order"]["quantity"] == 5
        assert data["order"]["status"] == "pending"
        assert "id" in data["order"]

    def test_create_order_missing_fields(self, client):
        payload = {"item": "widget-a"}  # Missing quantity and customer
        response = client.post(
            "/api/v1/orders",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["code"] == "MISSING_FIELDS"

    def test_create_order_invalid_quantity(self, client):
        payload = {"item": "widget-a", "quantity": -1, "customer": "acme-corp"}
        response = client.post(
            "/api/v1/orders",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert json.loads(response.data)["code"] == "INVALID_QUANTITY"

    def test_create_order_no_json(self, client):
        response = client.post("/api/v1/orders", data="not json")
        assert response.status_code == 400
        assert json.loads(response.data)["code"] == "INVALID_REQUEST"


class TestOrderRetrieval:
    """Tests for GET /api/v1/orders and GET /api/v1/orders/<id>."""

    def test_list_orders_empty(self, client):
        response = client.get("/api/v1/orders")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["count"] == 0

    def test_list_orders_after_create(self, client):
        # Create an order first
        payload = {"item": "widget-b", "quantity": 3, "customer": "globex"}
        client.post(
            "/api/v1/orders",
            data=json.dumps(payload),
            content_type="application/json",
        )

        response = client.get("/api/v1/orders")
        data = json.loads(response.data)
        assert data["count"] >= 1

    def test_get_order_by_id(self, client):
        # Create an order
        payload = {"item": "widget-c", "quantity": 1, "customer": "initech"}
        create_resp = client.post(
            "/api/v1/orders",
            data=json.dumps(payload),
            content_type="application/json",
        )
        order_id = json.loads(create_resp.data)["order"]["id"]

        # Retrieve it
        response = client.get(f"/api/v1/orders/{order_id}")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["order"]["id"] == order_id

    def test_get_order_not_found(self, client):
        response = client.get("/api/v1/orders/nonexistent-id")
        assert response.status_code == 404
        assert json.loads(response.data)["code"] == "NOT_FOUND"

    def test_filter_orders_by_status(self, client):
        # Create an order
        payload = {"item": "widget-d", "quantity": 2, "customer": "umbrella"}
        client.post(
            "/api/v1/orders",
            data=json.dumps(payload),
            content_type="application/json",
        )

        # Filter by status
        response = client.get("/api/v1/orders?status=pending")
        data = json.loads(response.data)
        assert all(o["status"] == "pending" for o in data["orders"])


class TestOrderUpdate:
    """Tests for PATCH /api/v1/orders/<id>."""

    def test_update_order_status(self, client):
        # Create an order
        payload = {"item": "widget-e", "quantity": 1, "customer": "wayne-ent"}
        create_resp = client.post(
            "/api/v1/orders",
            data=json.dumps(payload),
            content_type="application/json",
        )
        order_id = json.loads(create_resp.data)["order"]["id"]

        # Update status
        response = client.patch(
            f"/api/v1/orders/{order_id}",
            data=json.dumps({"status": "processing"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert json.loads(response.data)["order"]["status"] == "processing"

    def test_update_order_invalid_status(self, client):
        # Create an order
        payload = {"item": "widget-f", "quantity": 1, "customer": "stark-ind"}
        create_resp = client.post(
            "/api/v1/orders",
            data=json.dumps(payload),
            content_type="application/json",
        )
        order_id = json.loads(create_resp.data)["order"]["id"]

        # Try invalid status
        response = client.patch(
            f"/api/v1/orders/{order_id}",
            data=json.dumps({"status": "invalid"}),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert json.loads(response.data)["code"] == "INVALID_STATUS"

    def test_update_nonexistent_order(self, client):
        response = client.patch(
            "/api/v1/orders/fake-id",
            data=json.dumps({"status": "shipped"}),
            content_type="application/json",
        )
        assert response.status_code == 404


class TestOrderDeletion:
    """Tests for DELETE /api/v1/orders/<id>."""

    def test_delete_order(self, client):
        # Create an order
        payload = {"item": "widget-g", "quantity": 1, "customer": "oscorp"}
        create_resp = client.post(
            "/api/v1/orders",
            data=json.dumps(payload),
            content_type="application/json",
        )
        order_id = json.loads(create_resp.data)["order"]["id"]

        # Delete it
        response = client.delete(f"/api/v1/orders/{order_id}")
        assert response.status_code == 200

        # Verify it's gone
        get_resp = client.get(f"/api/v1/orders/{order_id}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_order(self, client):
        response = client.delete("/api/v1/orders/fake-id")
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════
#  PIPELINE STATUS
# ═══════════════════════════════════════════════════════════════


class TestPipelineStatus:
    """Tests for GET /api/v1/status."""

    def test_status_returns_200(self, client):
        response = client.get("/api/v1/status")
        assert response.status_code == 200

    def test_status_contains_security_info(self, client):
        response = client.get("/api/v1/status")
        data = json.loads(response.data)
        assert "security" in data
        assert "runtime" in data
        assert data["service"] == "container-security-falcon"
