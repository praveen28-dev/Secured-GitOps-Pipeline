# Container Security Falcon — Security Controls

This document catalogs every security control implemented in the project, maps each to recognized standards, and explains the threat model.

---

## 1. Security Controls Inventory

### Build-Time Security

| Control | Implementation | Standard |
|---------|---------------|----------|
| **Multi-stage Docker builds** | Builder stage discarded; only runtime deps in final image | CIS Docker Benchmark 4.1 |
| **Pinned base image versions** | `python:3.12-slim` — no `:latest` tags | CIS Docker Benchmark 4.2 |
| **Non-root user** | `USER appuser` (UID 1001) in Dockerfile | CIS Docker Benchmark 4.1 |
| **Minimal base image** | `python:3.12-slim` — no unnecessary packages | NIST SP 800-190 §4.1 |
| **No secrets in image layers** | Secrets via runtime env vars only | CIS Docker Benchmark 4.10 |
| **HEALTHCHECK instruction** | `HEALTHCHECK` defined in Dockerfile | CIS Docker Benchmark 4.6 |
| **.dockerignore** | Excludes `.env`, `.git`, tests, docs | CIS Docker Benchmark 4.10 |
| **OCI image labels** | Traceability metadata on every image | OCI Image Spec |

### Pipeline Security

| Control | Implementation | Standard |
|---------|---------------|----------|
| **Dockerfile policy enforcement** | OPA/Conftest Rego policies | NIST SP 800-204C |
| **CVE vulnerability scanning** | Trivy with CRITICAL/HIGH gate | NIST SP 800-190 §4.2 |
| **Pipeline-as-Code** | GitHub Actions YAML (version controlled) | NIST SP 800-204C |
| **Least-privilege CI permissions** | Minimal `permissions` block in workflows | CIS Supply Chain Level 3 |
| **SARIF reporting** | Results uploaded to GitHub Security tab | OWASP CI/CD Top 10 |
| **Unit testing gate** | pytest must pass before build | SDLC Best Practice |
| **Linting gate** | flake8 must pass before build | SDLC Best Practice |

### Runtime Security

| Control | Implementation | Standard |
|---------|---------------|----------|
| **Non-root execution** | `user: "1001:1001"` in Compose | CIS Docker Benchmark 5.2 |
| **Read-only root filesystem** | `read_only: true` in Compose | CIS Docker Benchmark 5.12 |
| **No privilege escalation** | `no-new-privileges:true` security opt | CIS Docker Benchmark 5.25 |
| **Dropped Linux capabilities** | `cap_drop: ALL`, selective `cap_add` | CIS Docker Benchmark 5.3 |
| **Resource limits** | CPU and memory limits in Compose | CIS Docker Benchmark 5.10 |
| **Network isolation** | Separate frontend/backend/monitoring networks | CIS Docker Benchmark 5.29 |
| **Health checks** | All services have health checks | CIS Docker Benchmark 5.26 |
| **Writable tmpfs only** | `/tmp` mounted as tmpfs with noexec | CIS Docker Benchmark 5.12 |

### Application Security

| Control | Implementation | Standard |
|---------|---------------|----------|
| **Security headers** | X-Frame-Options, CSP, HSTS, etc. | OWASP Secure Headers |
| **Rate limiting** | Nginx rate limiting (10 req/s) | OWASP API Top 10 |
| **Input validation** | All API inputs validated | OWASP Top 10 A03 |
| **No server fingerprinting** | Server header removed | OWASP Secure Headers |
| **Request size limits** | 1MB max body via Nginx | OWASP API Top 10 |
| **HTTPS enforcement** | HSTS header with 1-year max-age | OWASP Top 10 A02 |

---

## 2. Threat Model

### Attack Surface

```
Internet → Nginx (port 80) → Flask App (port 8000) → In-Memory Store
                                    ↓
                              Prometheus (port 9090) → Grafana (port 3000)
```

### Threats and Mitigations

| Threat | Risk | Mitigation |
|--------|------|------------|
| **Container escape** | HIGH | Non-root user, dropped capabilities, no-new-privileges, read-only FS |
| **Supply chain attack** (base image) | HIGH | Pinned versions, Trivy CVE scan, OPA policy enforcement |
| **Privilege escalation** | HIGH | `no-new-privileges`, non-root user, minimal capabilities |
| **Secrets leakage** | HIGH | No secrets in image layers, .dockerignore, runtime env vars |
| **DDoS / brute force** | MEDIUM | Nginx rate limiting, request size limits, timeouts |
| **Data exfiltration** | MEDIUM | Read-only filesystem, network isolation, dropped capabilities |
| **Dependency vulnerability** | MEDIUM | Trivy scanning, `ignore-unfixed` for actionable results |
| **Image tampering** | MEDIUM | GHCR image signing (future), SHA-tagged images |
| **Information disclosure** | LOW | Server header removed, custom error responses, no stack traces in prod |

---

## 3. Compliance Mapping

| Framework | Relevant Controls |
|-----------|-------------------|
| **CIS Docker Benchmark v1.6** | 4.1, 4.2, 4.6, 4.10, 5.2, 5.3, 5.10, 5.12, 5.25, 5.26, 5.29 |
| **NIST SP 800-190** | Container image security, runtime security, orchestrator hardening |
| **NIST SP 800-204C** | DevSecOps pipeline controls, policy-as-code |
| **OWASP Top 10** | A02 (Crypto), A03 (Injection), A05 (Misconfig), A06 (Components) |
| **OWASP Docker Top 10** | D01-D10 coverage via CIS controls |

---

## 4. Incident Response

If a CVE is flagged by Trivy:

1. **Pipeline halts automatically** — no vulnerable image reaches production
2. Review the Trivy report in the GitHub Actions logs or Security tab
3. Check if the CVE has a fix available (`ignore-unfixed: true` helps here)
4. Update the affected dependency in `requirements.txt` or the base image
5. Re-run the pipeline — it will only deploy if clean
6. Document the CVE and resolution in the security log
