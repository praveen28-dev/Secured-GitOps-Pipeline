"""
Container Security Falcon — API Routes

Provides:
  - /health          → Container health check (required for orchestrators)
  - /ready           → Readiness probe
  - /api/v1/orders   → CRUD operations on orders (demo workload)
  - /api/v1/status   → Pipeline and security status
"""

import time
import uuid
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

# ── Blueprints ───────────────────────────────────────────────
health_bp = Blueprint("health", __name__)
api_bp = Blueprint("api", __name__)

# ── In-memory store (replaced by a database in production) ──
_orders: dict[str, dict] = {}
_start_time = time.time()


# ═══════════════════════════════════════════════════════════════
#  HEALTH & READINESS PROBES
# ═══════════════════════════════════════════════════════════════


@health_bp.route("/health", methods=["GET"])
def health_check():
    """Liveness probe — confirms the process is running.

    Used by Docker HEALTHCHECK and Kubernetes livenessProbe.
    Returns 200 if the application can serve requests.
    """
    uptime_seconds = round(time.time() - _start_time, 2)
    return jsonify({
        "status": "healthy",
        "service": "container-security-falcon",
        "uptime_seconds": uptime_seconds,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }), 200


@health_bp.route("/ready", methods=["GET"])
def readiness_check():
    """Readiness probe — confirms the app is ready to accept traffic.

    Used by Kubernetes readinessProbe and load balancers.
    Can include dependency checks (database, cache, etc.)
    """
    checks = {
        "application": "ready",
        "in_memory_store": "available",
    }

    all_ready = all(v in ("ready", "available") for v in checks.values())

    return jsonify({
        "status": "ready" if all_ready else "not_ready",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }), 200 if all_ready else 503


# ═══════════════════════════════════════════════════════════════
#  ORDER MANAGEMENT API (Demo Workload)
# ═══════════════════════════════════════════════════════════════


@api_bp.route("/orders", methods=["GET"])
def list_orders():
    """List all orders with optional status filtering."""
    status_filter = request.args.get("status")

    if status_filter:
        filtered = {
            k: v for k, v in _orders.items()
            if v["status"] == status_filter
        }
    else:
        filtered = _orders

    return jsonify({
        "count": len(filtered),
        "orders": list(filtered.values()),
    }), 200


@api_bp.route("/orders", methods=["POST"])
def create_order():
    """Create a new order.

    Expects JSON body:
    {
        "item": "widget-a",
        "quantity": 5,
        "customer": "acme-corp"
    }
    """
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "Request body must be valid JSON",
            "code": "INVALID_REQUEST",
        }), 400

    # Validate required fields
    required_fields = ["item", "quantity", "customer"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({
            "error": f"Missing required fields: {', '.join(missing)}",
            "code": "MISSING_FIELDS",
        }), 400

    # Validate quantity
    if not isinstance(data["quantity"], int) or data["quantity"] < 1:
        return jsonify({
            "error": "Quantity must be a positive integer",
            "code": "INVALID_QUANTITY",
        }), 400

    order_id = str(uuid.uuid4())
    order = {
        "id": order_id,
        "item": str(data["item"]),
        "quantity": int(data["quantity"]),
        "customer": str(data["customer"]),
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    _orders[order_id] = order

    return jsonify({
        "message": "Order created successfully",
        "order": order,
    }), 201


@api_bp.route("/orders/<order_id>", methods=["GET"])
def get_order(order_id: str):
    """Retrieve a specific order by ID."""
    order = _orders.get(order_id)

    if not order:
        return jsonify({
            "error": "Order not found",
            "code": "NOT_FOUND",
        }), 404

    return jsonify({"order": order}), 200


@api_bp.route("/orders/<order_id>", methods=["PATCH"])
def update_order_status(order_id: str):
    """Update an order's status.

    Expects JSON body:
    {
        "status": "processing" | "shipped" | "delivered" | "cancelled"
    }
    """
    order = _orders.get(order_id)

    if not order:
        return jsonify({
            "error": "Order not found",
            "code": "NOT_FOUND",
        }), 404

    data = request.get_json(silent=True)
    if not data or "status" not in data:
        return jsonify({
            "error": "Request body must include 'status' field",
            "code": "MISSING_STATUS",
        }), 400

    valid_statuses = {"pending", "processing", "shipped", "delivered", "cancelled"}
    if data["status"] not in valid_statuses:
        return jsonify({
            "error": f"Invalid status. Must be one of: {', '.join(sorted(valid_statuses))}",
            "code": "INVALID_STATUS",
        }), 400

    order["status"] = data["status"]
    order["updated_at"] = datetime.now(timezone.utc).isoformat()

    return jsonify({
        "message": "Order updated successfully",
        "order": order,
    }), 200


@api_bp.route("/orders/<order_id>", methods=["DELETE"])
def delete_order(order_id: str):
    """Delete an order by ID."""
    if order_id not in _orders:
        return jsonify({
            "error": "Order not found",
            "code": "NOT_FOUND",
        }), 404

    del _orders[order_id]

    return jsonify({
        "message": "Order deleted successfully",
        "id": order_id,
    }), 200


# ═══════════════════════════════════════════════════════════════
#  PIPELINE & SECURITY STATUS
# ═══════════════════════════════════════════════════════════════


@api_bp.route("/status", methods=["GET"])
def pipeline_status():
    """Return pipeline and security posture information.

    Demonstrates the kind of metadata a secured container exposes.
    """
    import os

    return jsonify({
        "service": "container-security-falcon",
        "version": os.getenv("APP_VERSION", "0.1.0"),
        "environment": os.getenv("APP_ENV", "development"),
        "security": {
            "non_root_user": os.getuid() != 0 if hasattr(os, "getuid") else "N/A (Windows)",
            "read_only_fs": os.getenv("READ_ONLY_FS", "false"),
            "capabilities_dropped": os.getenv("CAPS_DROPPED", "unknown"),
            "image_scanned": os.getenv("IMAGE_SCANNED", "false"),
            "scan_result": os.getenv("SCAN_RESULT", "unknown"),
        },
        "runtime": {
            "hostname": os.getenv("HOSTNAME", "localhost"),
            "pid": os.getpid(),
            "uptime_seconds": round(time.time() - _start_time, 2),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }), 200
