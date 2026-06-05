# Container Security Falcon — Architecture

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          DEVELOPER WORKSTATION                          │
│                                                                          │
│   Code Change → git commit → git push → GitHub (main branch)            │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      GITHUB ACTIONS CI/CD PIPELINE                       │
│                                                                          │
│   ┌────────────┐   ┌──────────────────┐   ┌────────────────────┐        │
│   │ LINT & TEST │──▶│  CONFTEST (OPA)   │──▶│   DOCKER BUILD     │       │
│   │ pytest      │   │  Dockerfile       │   │   Multi-Stage      │       │
│   │ flake8      │   │  Policy Gate 🛡️   │   │   Non-Root         │       │
│   └────────────┘   └──────────────────┘   └────────┬───────────┘        │
│                                                      │                    │
│   ┌────────────────┐   ┌──────────────────┐   ┌─────▼──────────┐        │
│   │ PUSH TO GHCR   │◀──│  TRIVY CVE SCAN  │◀──│  IMAGE READY   │       │
│   │ (if clean)     │   │  CRITICAL/HIGH   │   │                │        │
│   │                │   │  = HALT 🛡️       │   │                │        │
│   └───────┬────────┘   └──────────────────┘   └────────────────┘        │
│           │                                                               │
│   ┌───────▼────────────────────────────────────────────────────┐         │
│   │ DEPLOY (Docker Compose with Runtime Security Restrictions)  │         │
│   │   • Non-root (UID 1001)      • Read-only filesystem        │         │
│   │   • Dropped capabilities     • No privilege escalation     │         │
│   │   • Network isolation        • Resource limits             │         │
│   │   • Health check gate 🛡️                                   │         │
│   └────────────────────────────────────────────────────────────┘         │
└──────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        RUNTIME ENVIRONMENT                               │
│                                                                          │
│  ┌─────────────┐   ┌──────────┐   ┌───────────┐   ┌───────────────┐    │
│  │  Flask App   │◀──│  Nginx   │   │Prometheus │──▶│   Grafana     │    │
│  │  Port 8000   │   │  Port 80 │   │ Port 9090 │   │  Port 3000    │    │
│  │  (backend)   │   │(frontend)│   │(monitoring)│   │ (monitoring)  │    │
│  └─────────────┘   └──────────┘   └───────────┘   └───────────────┘    │
│                                                                          │
│  Networks: frontend ←→ backend ←→ monitoring (isolated)                  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Pipeline Stages Explained

### Stage 1: Lint & Test
- **What**: Static code analysis (flake8) and unit tests (pytest)
- **Why**: Catches bugs and code quality issues before any build happens
- **Gate**: Pipeline halts if tests fail or critical lint errors found

### Stage 2: Conftest (OPA Policy Gate)
- **What**: Validates `Dockerfile` against Rego security policies
- **Why**: "Shift left" — catch Dockerfile security issues before building
- **Checks**: No `:latest` tags, `USER` instruction present, no `ADD`, no secrets in `ENV`
- **Gate**: Pipeline halts if any `deny` rule triggers

### Stage 3: Docker Build
- **What**: Multi-stage build producing a minimal runtime image
- **Why**: Builder stage (with gcc, build tools) is discarded — only runtime deps ship
- **Security**: Non-root user, pinned versions, HEALTHCHECK, OCI labels

### Stage 4: Trivy CVE Scan
- **What**: Scans the built image for known CVEs in OS packages and Python libraries
- **Why**: Prevents deployment of images with known vulnerabilities
- **Gate**: Pipeline HALTS on any CRITICAL or HIGH severity CVE
- **Reporting**: Results uploaded to GitHub Security tab as SARIF

### Stage 5: Push to GHCR
- **What**: Pushes the verified image to GitHub Container Registry
- **Why**: Only images that pass ALL gates are published
- **Tags**: SHA commit hash, branch name, `latest` for main

### Stage 6: Deploy with Runtime Security
- **What**: Docker Compose deployment with comprehensive runtime restrictions
- **Why**: Demonstrates defense-in-depth — even if the image is compromised, runtime controls limit damage
- **Gate**: Smoke test verifies health endpoint and confirms non-root execution

---

## Network Architecture

```
Internet
    │
    ▼
┌──────────┐     ┌───────────┐
│  Nginx   │────▶│ Flask App │
│ (public) │     │ (private) │
└──────────┘     └─────┬─────┘
  frontend net      backend net
                       │
                 ┌─────▼─────┐     ┌──────────┐
                 │ Prometheus │────▶│ Grafana  │
                 │            │     │          │
                 └────────────┘     └──────────┘
                   monitoring net
```

- **Frontend network**: Only Nginx and the app — Nginx is the only internet-facing service
- **Backend network**: App and Prometheus — internal communication only
- **Monitoring network**: Prometheus and Grafana — isolated from application traffic

---

## Decision Log

| Decision | Rationale |
|----------|-----------|
| **GitHub Actions over AWS CodePipeline** | Zero cost for public repos; 2000 free minutes/month for private |
| **GHCR over Amazon ECR** | Free for public repos; integrated with GitHub Actions via `GITHUB_TOKEN` |
| **Trivy over ECR Enhanced Scanning** | Open source, runs anywhere, SARIF output for GitHub Security |
| **Docker Compose over ECS Fargate** | Zero cost; demonstrates identical runtime security concepts |
| **Python Flask over Node.js/Go** | Lightweight, clear security demonstration, fast build times |
| **python:3.12-slim over Alpine** | Better binary wheel support, fewer compatibility issues |
| **Gunicorn over Flask dev server** | Production-grade WSGI server with worker management |
| **Prometheus+Grafana over CloudWatch** | Open source, zero cost, industry standard |
| **OPA/Conftest for policies** | Industry-standard policy-as-code, works with any Dockerfile |
