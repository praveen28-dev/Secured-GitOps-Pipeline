# Container Security Falcon — Operational Runbook

## Table of Contents
- [Quick Start](#quick-start)
- [Responding to CVE Findings](#responding-to-cve-findings)
- [Updating Base Images](#updating-base-images)
- [Rotating Secrets](#rotating-secrets)
- [Troubleshooting](#troubleshooting)
- [Emergency Procedures](#emergency-procedures)

---

## Quick Start

### Prerequisites
- Docker Desktop installed
- Git installed
- GitHub account with repository access

### Local Development

```bash
# Clone the repository
git clone https://github.com/<your-user>/container-security-falcon.git
cd container-security-falcon

# Build and run locally
docker compose up -d --build

# Verify services
curl http://localhost:8000/health    # Direct app access
curl http://localhost:80/health      # Via Nginx proxy
curl http://localhost:9090           # Prometheus
open http://localhost:3000           # Grafana (admin/admin)
```

### Run Tests Locally

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v --cov=app

# Run linting
flake8 app/ tests/ --max-line-length=120
```

### Validate Dockerfile Policies Locally

```bash
# Install Conftest
# On macOS: brew install conftest
# On Linux: Download from https://github.com/open-policy-agent/conftest/releases

# Run policy check
conftest test Dockerfile --policy policy/
```

### Run Trivy Scan Locally

```bash
# Install Trivy
# On macOS: brew install aquasecurity/trivy/trivy
# On Linux: See https://aquasecurity.github.io/trivy/latest/getting-started/installation/

# Build image
docker build -t falcon:test .

# Scan
trivy image falcon:test --severity CRITICAL,HIGH
```

---

## Responding to CVE Findings

### When the pipeline halts due to a CVE:

1. **Check the GitHub Actions log** for the Trivy scan output
2. **Identify the affected package** from the scan results table
3. **Assess the CVE**:
   - Is it in the base image or a Python dependency?
   - Is a fix available? (Trivy uses `ignore-unfixed: true`)
   - What is the CVSS score and attack vector?

4. **If fix is available in a Python dependency**:
   ```bash
   # Update requirements.txt with the fixed version
   pip install --upgrade <package-name>
   pip freeze | grep <package-name>
   # Update requirements.txt
   # Commit and push
   ```

5. **If fix is available in the base image**:
   ```bash
   # Update the base image version in Dockerfile
   # e.g., python:3.12.5-slim → python:3.12.6-slim
   # Commit and push
   ```

6. **If no fix is available but you need to deploy**:
   - Add the CVE to `.trivyignore` file:
     ```
     # CVE-2024-XXXXX: Not exploitable in our context
     # Reason: <explain why this is acceptable>
     # Review date: <date to re-check>
     CVE-2024-XXXXX
     ```
   - Document the risk acceptance decision

### Trivy Ignore File Format

Create `.trivyignore` in the project root:
```
# Vulnerabilities accepted with documented justification
# Format: CVE-ID

# Example: glibc vulnerability not exploitable in our non-root container
# Reviewed: 2024-01-15, Review again: 2024-04-15
CVE-2023-XXXXX
```

---

## Updating Base Images

### Schedule
- Check for base image updates **monthly**
- Check immediately when notified of CVEs in Python or Debian

### Process

1. Check for new versions:
   ```bash
   # Check Docker Hub for available tags
   docker pull python:3.12-slim
   docker inspect python:3.12-slim | grep -i version
   ```

2. Update `Dockerfile`:
   ```dockerfile
   FROM python:3.12.X-slim AS builder
   # ... (update both stages)
   FROM python:3.12.X-slim AS runtime
   ```

3. Test locally:
   ```bash
   docker build -t falcon:test .
   trivy image falcon:test --severity CRITICAL,HIGH
   docker compose up -d --build
   curl http://localhost:8000/health
   ```

4. Commit, push, and verify the pipeline passes

---

## Rotating Secrets

### Application Secrets

1. Generate a new secret key:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. Update the GitHub repository secret:
   - Go to **Settings → Secrets and variables → Actions**
   - Update `SECRET_KEY`

3. Trigger a redeployment

### Grafana Admin Password

1. Update `GRAFANA_PASSWORD` environment variable
2. Restart Grafana container:
   ```bash
   docker compose restart grafana
   ```

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs app

# Check if read-only FS is causing issues
# The app needs /tmp for temporary files
docker compose exec app ls -la /tmp

# Verify the user
docker compose exec app whoami
# Should return: appuser
```

### Health check failing

```bash
# Check if the app is actually running
docker compose exec app curl http://localhost:8000/health

# Check Nginx connectivity
docker compose logs nginx

# Check network connectivity
docker network inspect falcon-frontend
```

### Trivy scan timing out

```bash
# Increase timeout in the workflow
# Or run locally with a longer timeout:
trivy image --timeout 10m falcon:latest
```

### Conftest failing unexpectedly

```bash
# Debug by running in verbose mode
conftest test Dockerfile --policy policy/ --trace

# Check if Rego policies have syntax errors
conftest verify --policy policy/
```

---

## Emergency Procedures

### Rollback Deployment

```bash
# Stop current deployment
docker compose down

# Pull the previous known-good image
docker pull ghcr.io/<user>/container-security-falcon:<previous-sha>

# Deploy with the specific tag
IMAGE_TAG=ghcr.io/<user>/container-security-falcon:<previous-sha> \
  docker compose up -d
```

### Disable Security Gate (Emergency Only)

> ⚠️ **WARNING**: Only do this in a genuine emergency. Document the decision.

In `.github/workflows/security-pipeline.yml`, temporarily change:
```yaml
exit-code: '0'  # Changed from '1' — EMERGENCY BYPASS
```

Create a follow-up issue immediately to re-enable the gate.
