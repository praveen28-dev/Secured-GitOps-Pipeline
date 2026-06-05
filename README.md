# 🛡️ Container Security Falcon

### A Hardened GitOps Pipeline for Container-Based Microservices

[![Security Pipeline](https://github.com/YOUR_USER/container-security-falcon/actions/workflows/security-pipeline.yml/badge.svg)](https://github.com/YOUR_USER/container-security-falcon/actions/workflows/security-pipeline.yml)
[![PR Check](https://github.com/YOUR_USER/container-security-falcon/actions/workflows/pr-check.yml/badge.svg)](https://github.com/YOUR_USER/container-security-falcon/actions/workflows/pr-check.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **Zero cloud cost.** This project demonstrates enterprise-grade container security using entirely free tools and infrastructure.

---

## 🎯 What This Project Demonstrates

```
[Git Commit] ──► [GitHub Actions Pipeline] ──► [Docker Build (Non-Root/Alpine)]
                                                         │
                                                         ▼
[Deploy (Least Privilege Runtime)] ◄───────── [Trivy CVE Scan (Pass/Fail)]
```

A complete **DevSecOps pipeline** that:

1. **Validates** Dockerfile security policies using OPA/Conftest (Policy-as-Code)
2. **Builds** hardened Docker images with multi-stage builds and non-root execution
3. **Scans** for CVE vulnerabilities using Trivy — halts deployment on CRITICAL/HIGH
4. **Deploys** with strict runtime restrictions (read-only FS, dropped capabilities, network isolation)
5. **Monitors** with Prometheus + Grafana dashboards

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    GITHUB ACTIONS PIPELINE                           │
│                                                                     │
│  ┌──────────┐   ┌──────────────┐   ┌────────────┐   ┌───────────┐ │
│  │ Lint &    │──▶│ Conftest/OPA │──▶│Docker Build│──▶│ Push GHCR │ │
│  │ Test      │   │ Policy Gate  │   │Multi-Stage │   │           │ │
│  │           │   │ 🛡️ Gate 1    │   │            │   │           │ │
│  └──────────┘   └──────────────┘   └────────────┘   └─────┬─────┘ │
│                                                            │       │
│  ┌──────────────┐   ┌──────────────────┐                   │       │
│  │ DEPLOY       │◀──│  TRIVY CVE SCAN  │◀──────────────────┘       │
│  │ 🛡️ Gate 3    │   │  🛡️ Gate 2       │                           │
│  └──────────────┘   └──────────────────┘                           │
└─────────────────────────────────────────────────────────────────────┘
```

### Three Security Gates

| Gate | Tool | What It Checks | Failure = |
|------|------|---------------|-----------|
| 🛡️ **Gate 1** | Conftest (OPA) | Dockerfile policies: non-root, pinned versions, no secrets | Pipeline HALT |
| 🛡️ **Gate 2** | Trivy | CVE vulnerabilities: CRITICAL and HIGH severity | Pipeline HALT |
| 🛡️ **Gate 3** | Smoke Test | Health check + non-root execution verification | Rollback |

---

## 🔒 Security Controls

### Build-Time
- ✅ Multi-stage Docker builds (minimal attack surface)
- ✅ Pinned base image versions (no `:latest`)
- ✅ Non-root user (UID 1001)
- ✅ No secrets in image layers
- ✅ `.dockerignore` prevents sensitive file leakage
- ✅ OPA/Conftest policy enforcement

### Runtime
- ✅ Read-only root filesystem
- ✅ All Linux capabilities dropped (`cap_drop: ALL`)
- ✅ No privilege escalation (`no-new-privileges`)
- ✅ Resource limits (CPU + memory)
- ✅ Network isolation (separate frontend/backend/monitoring)
- ✅ Health checks on all services

### Pipeline
- ✅ Trivy CVE scanning with CRITICAL/HIGH gate
- ✅ SARIF reports uploaded to GitHub Security tab
- ✅ Least-privilege GitHub Actions permissions
- ✅ Automated rollback on deployment failure

---

## 💰 Zero-Cost Stack

| Component | Tool | Cost |
|-----------|------|------|
| CI/CD Pipeline | GitHub Actions | Free (public repos) |
| Container Registry | GitHub Container Registry (GHCR) | Free (public repos) |
| CVE Scanning | Trivy (open source) | Free |
| Policy Enforcement | Conftest/OPA (open source) | Free |
| Monitoring | Prometheus + Grafana (self-hosted) | Free |
| Deployment | Docker Compose (local) | Free |
| Cloud Hosting (optional) | Oracle Cloud Always Free | Free (forever) |

---

## 🚀 Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Git](https://git-scm.com/)
- Python 3.12+ (for local development)

### 1. Clone and Run

```bash
git clone https://github.com/YOUR_USER/container-security-falcon.git
cd container-security-falcon

# Start all services
docker compose up -d --build
```

### 2. Verify

```bash
# Application health
curl http://localhost:8000/health

# API endpoint
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"item": "widget-a", "quantity": 5, "customer": "acme-corp"}'

# Security status
curl http://localhost:8000/api/v1/status

# Verify non-root
docker exec falcon-app whoami
# → appuser (NOT root)

# Verify read-only filesystem
docker exec falcon-app touch /test
# → touch: cannot touch '/test': Read-only file system ✅
```

### 3. Access Dashboards

| Service | URL | Credentials |
|---------|-----|-------------|
| Application | http://localhost:8000 | — |
| Nginx Proxy | http://localhost:80 | — |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3000 | admin / admin |

### 4. Run Tests

```bash
pip install -r requirements.txt
pytest tests/ -v --cov=app
```

### 5. Validate Security Policies

```bash
# Install Conftest: https://www.conftest.dev/install/
conftest test Dockerfile --policy policy/
```

---

## 📁 Project Structure

```
container-security-falcon/
├── .github/workflows/
│   ├── security-pipeline.yml    # Main CI/CD with 3 security gates
│   └── pr-check.yml             # Lightweight PR validation
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── config.py                # Environment-based config
│   └── routes.py                # API endpoints + security headers
├── tests/
│   └── test_app.py              # 25+ unit tests
├── policy/
│   └── dockerfile.rego          # OPA security policies
├── nginx/
│   └── nginx.conf               # Reverse proxy + rate limiting
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/
│       ├── dashboards/
│       └── provisioning/
├── terraform/                   # (Optional) Oracle Cloud IaC
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── cloud-init.yaml
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SECURITY.md
│   └── RUNBOOK.md
├── Dockerfile                   # Hardened multi-stage
├── .dockerignore
├── docker-compose.yml           # Runtime security
├── docker-compose.prod.yml      # Production overrides
└── requirements.txt
```

---

## 🧪 Testing the Security Gates

### Test Gate 1 (Dockerfile Policy)
```bash
# Intentionally break a policy — add `:latest` to Dockerfile
# The pipeline will HALT with a policy violation
```

### Test Gate 2 (CVE Scan)
```bash
# Use an old base image with known CVEs
# FROM python:3.9-slim  (has known vulnerabilities)
# The pipeline will HALT with Trivy findings
```

### Test Gate 3 (Smoke Test)
```bash
# Break the health endpoint
# The pipeline will rollback the deployment
```

---

## 📊 Skills Demonstrated

| Skill Area | Specifics |
|------------|-----------|
| **Container Security** | Multi-stage builds, non-root execution, read-only FS, dropped capabilities |
| **CI/CD Pipeline Design** | Multi-stage pipeline with security gates, automated rollback |
| **Policy-as-Code** | OPA/Rego policies for Dockerfile enforcement |
| **Vulnerability Management** | Trivy CVE scanning, SARIF reporting, remediation workflow |
| **Infrastructure as Code** | Terraform for Oracle Cloud (optional) |
| **Monitoring & Observability** | Prometheus metrics, Grafana dashboards |
| **Network Security** | Nginx reverse proxy, rate limiting, security headers, network isolation |
| **Principle of Least Privilege** | Minimal capabilities, non-root, restricted FS, least-privilege CI tokens |

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -m 'Add improvement'`)
4. Push to branch (`git push origin feature/improvement`)
5. Open a Pull Request

The PR Check workflow will automatically validate your changes against security policies.
