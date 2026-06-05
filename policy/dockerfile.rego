# ============================================================
# Container Security Falcon — Dockerfile Security Policies
#
# These OPA/Rego policies enforce security standards for
# Dockerfiles BEFORE the image is even built.
#
# Usage:
#   conftest test Dockerfile --policy policy/
#
# This is "shifting security left" — catching issues at the
# earliest possible stage in the pipeline.
# ============================================================

package main

import rego.v1

# ── DENY: Using 'latest' tag ────────────────────────────────
# The 'latest' tag is mutable and makes builds non-reproducible.
# Always pin to a specific version.
deny contains msg if {
    input[i].Cmd == "from"
    val := input[i].Value[0]
    not contains(val, "as")
    not contains(val, ":")
    msg := sprintf("Line %d: Base image '%s' has no tag. Pin to a specific version (e.g., python:3.12-slim)", [i + 1, val])
}

deny contains msg if {
    input[i].Cmd == "from"
    val := input[i].Value[0]
    endswith(val, ":latest")
    msg := sprintf("Line %d: Do not use ':latest' tag for base image '%s'. Pin to a specific version", [i + 1, val])
}

# ── DENY: Running as root ───────────────────────────────────
# Containers should never run as root. A USER instruction
# must be present to switch to a non-privileged user.
deny contains msg if {
    not any_user_instruction
    msg := "Dockerfile must include a USER instruction to run as non-root"
}

any_user_instruction if {
    input[i].Cmd == "user"
}

# ── DENY: Explicit root user ────────────────────────────────
# Even if USER is specified, it should not be 'root'
deny contains msg if {
    input[i].Cmd == "user"
    input[i].Value[0] == "root"
    msg := sprintf("Line %d: USER should not be 'root'. Use a dedicated non-root user", [i + 1])
}

# ── DENY: Using ADD instead of COPY ─────────────────────────
# ADD has implicit behaviors (auto-extraction, URL fetching)
# that can introduce security risks. Always use COPY.
deny contains msg if {
    input[i].Cmd == "add"
    msg := sprintf("Line %d: Use COPY instead of ADD. ADD can auto-extract archives and fetch URLs, which is a security risk", [i + 1])
}

# ── WARN: No HEALTHCHECK ────────────────────────────────────
# HEALTHCHECK is important for container orchestrators to
# determine if the application is actually functional.
warn contains msg if {
    not any_healthcheck
    msg := "Dockerfile should include a HEALTHCHECK instruction for orchestrator integration"
}

any_healthcheck if {
    input[i].Cmd == "healthcheck"
}

# ── DENY: Secrets in ENV instructions ───────────────────────
# Environment variables baked into the image are visible in
# docker inspect and image layers. Never put secrets here.
deny contains msg if {
    input[i].Cmd == "env"
    val := input[i].Value[0]
    contains(lower(val), "password")
    msg := sprintf("Line %d: Potential secret in ENV instruction. Never embed passwords in Dockerfiles — use runtime secrets instead", [i + 1])
}

deny contains msg if {
    input[i].Cmd == "env"
    val := input[i].Value[0]
    contains(lower(val), "secret_key")
    msg := sprintf("Line %d: Potential secret in ENV instruction. Never embed secret keys in Dockerfiles — use runtime secrets instead", [i + 1])
}

deny contains msg if {
    input[i].Cmd == "env"
    val := input[i].Value[0]
    contains(lower(val), "api_key")
    msg := sprintf("Line %d: Potential secret in ENV instruction. Never embed API keys in Dockerfiles — use runtime secrets instead", [i + 1])
}

deny contains msg if {
    input[i].Cmd == "env"
    val := input[i].Value[0]
    contains(lower(val), "aws_access")
    msg := sprintf("Line %d: Potential AWS credential in ENV instruction. Never embed cloud credentials in Dockerfiles", [i + 1])
}

# ── WARN: Using apt-get without cleanup ──────────────────────
# Package manager caches should be removed to reduce image size
# and avoid including package metadata in the final image.
warn contains msg if {
    input[i].Cmd == "run"
    val := concat(" ", input[i].Value)
    contains(val, "apt-get install")
    not contains(val, "rm -rf /var/lib/apt/lists")
    msg := sprintf("Line %d: apt-get install should be followed by 'rm -rf /var/lib/apt/lists/*' to reduce image size", [i + 1])
}

# ── WARN: Using pip without --no-cache-dir ───────────────────
# pip cache is unnecessary in containers and adds to image size.
warn contains msg if {
    input[i].Cmd == "run"
    val := concat(" ", input[i].Value)
    contains(val, "pip install")
    not contains(val, "--no-cache-dir")
    msg := sprintf("Line %d: pip install should use --no-cache-dir to reduce image size", [i + 1])
}
