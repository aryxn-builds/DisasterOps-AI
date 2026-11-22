# Deployment and operations

This runbook distinguishes the checked-in loopback setup from proposed staging. Read [Security](SECURITY.md) before allowing network access.

## Current local development

Follow [README setup](../README.md#run-locally). Use a dedicated PostgreSQL database, then apply Alembic before starting via `python server.py`. The entry point binds loopback port 8000 and disables Uvicorn access logs. Provision staff with the interactive operator CLI. Do not apply historical SQL. For a clean smoke run, verify API docs, anonymous denial, an authorized SOS acknowledgment and a confirmed simulated assignment.

| Configuration | Responsibility |
| --- | --- |
| DATABASE_URL | Required PostgreSQL connection. Standard postgresql scheme maps to pg8000. |
| SERVER_PUBLIC_URL, SECURE_COOKIES | Exact browser origin and secure-cookie mode. HTTP with insecure cookies is an explicit loopback dev option. |
| SESSION_SECONDS | Session TTL, bounded to 60–86,400 seconds. |
| EMERGENCY_SMS_GATEWAY_NUMBER | Optional project SIM exposed via config. |
| ANDROID_SMS_GATEWAY_WEBHOOK_SECRET | Optional inbound signing key. Empty or missing disables intake. |
| ANDROID_SMS_GATEWAY_URL, ANDROID_SMS_GATEWAY_USER, ANDROID_SMS_GATEWAY_PASSWORD | Optional outbound consent transport. Configure all three together and protect credentials and egress. |
| TEST_DATABASE_URL | Test-only database for isolated PostgreSQL schema checks. |

## Proposed staging and Docker

No Dockerfile, Compose file, CI manifest or deployment configuration is checked in. A staging design would put HTTPS and body/rate limits at the edge, restrict the database and gateway egress, inject secrets, and separate migration privileges from runtime credentials. If Docker is approved, use a pinned runtime image, unprivileged user, immutable app assets, and a dedicated migration job. Persist PostgreSQL outside web containers. Add readiness checks, backup, restoration and controlled promotion. Test on synthetic fixtures with a controlled gateway, and gate external actions behind explicit approval.

## Change and recovery

Before promotion, verify the configured origin, cookie flags, TLS, role access, log redaction, migration parity, database restore and authorized gateway configuration. Take a protected backup and test recovery before schema changes. Prefer additive compatible migrations and an explicit rollback/roll-forward plan. Coordinate with operators if intake is unavailable; an unacknowledged SOS may need retry with the original key. Use procedure and permissions from [Security](SECURITY.md), [Data model](DATA_MODEL.md) and [Testing strategy](../TESTING_STRATEGY.md).
