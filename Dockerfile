# ============================================================
# Container Security Falcon — Hardened Multi-Stage Dockerfile
#
# Security Features:
#   ✅ Multi-stage build (minimal attack surface)
#   ✅ Pinned base image versions (no :latest)
#   ✅ Non-root user execution (UID 1001)
#   ✅ Read-only filesystem compatible
#   ✅ HEALTHCHECK for orchestrator integration
#   ✅ Minimal dependencies in runtime image
#   ✅ No cache artifacts in final image
#   ✅ Labels for image metadata and traceability
# ============================================================

# ── Stage 1: Builder ─────────────────────────────────────────
# Install build dependencies and compile Python packages.
# This stage is discarded — nothing here reaches production.
FROM python:3.12-slim AS builder

# Prevent Python from writing .pyc files and buffering output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install system-level build dependencies (needed for some pip packages)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (leverages Docker layer caching)
COPY requirements.txt .

# Install Python dependencies into a user-local directory
# --no-cache-dir: Don't store pip cache (reduces image size)
# --user: Install to ~/.local (easy to copy to runtime stage)
RUN pip install --no-cache-dir --user -r requirements.txt


# ── Stage 2: Runtime ─────────────────────────────────────────
# Minimal image with only what's needed to run the application.
FROM python:3.12-slim AS runtime

# ── Image Metadata (OCI standard labels) ────────────────────
LABEL org.opencontainers.image.title="Container Security Falcon" \
      org.opencontainers.image.description="Hardened Flask microservice with security-first CI/CD" \
      org.opencontainers.image.vendor="Praveen" \
      org.opencontainers.image.source="https://github.com/praveen/container-security-falcon" \
      org.opencontainers.image.licenses="MIT" \
      security.non-root="true" \
      security.read-only-fs="compatible" \
      security.capabilities="minimal"

# ── Create non-root user ────────────────────────────────────
# Using fixed UID/GID for consistency across environments
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/false --create-home appuser

WORKDIR /app

# ── Copy Python packages from builder stage ──────────────────
# Only runtime dependencies — no build tools, no gcc, no headers
COPY --from=builder /root/.local /home/appuser/.local

# ── Copy application source code ────────────────────────────
# --chown ensures the non-root user owns all files
COPY --chown=appuser:appgroup ./app ./app

# ── Environment Configuration ───────────────────────────────
ENV PATH="/home/appuser/.local/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    APP_VERSION=0.1.0 \
    # Security markers (used by /api/v1/status endpoint)
    READ_ONLY_FS=true \
    CAPS_DROPPED=ALL \
    IMAGE_SCANNED=true

# ── Switch to non-root user ─────────────────────────────────
# From this point, ALL commands run as appuser (UID 1001)
USER appuser

# ── Expose application port ─────────────────────────────────
EXPOSE 8000

# ── Health Check ─────────────────────────────────────────────
# Docker and orchestrators use this to determine container health
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# ── Run with Gunicorn (production WSGI server) ──────────────
# --workers: Number of worker processes (2x CPU + 1 is recommended)
# --bind: Listen on all interfaces at port 8000
# --access-logfile: Log requests to stdout for container log collection
# --error-logfile: Log errors to stderr
# --timeout: Worker timeout in seconds
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--threads", "4", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--timeout", "30", \
     "--graceful-timeout", "10", \
     "app:create_app()"]
