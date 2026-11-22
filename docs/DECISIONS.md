# Architecture decision records

This index records decisions inferred from the checked-out implementation and explicitly open research choices. Status describes the decision, not deployment readiness.

| ID and status | Decision, rationale and consequence |
| --- | --- |
| ADR-001 Adopted | Modular monolith with same-origin browser. Keeps transaction and trust boundaries local. Add workers or service separation only when evidence supports it. See [architecture](ARCHITECTURE.md). |
| ADR-002 Adopted | PostgreSQL plus Alembic replaces seeded memory; start from a fresh schema and preserve old SQL as history. SQLite is a fast test substitute only. |
| ADR-003 Adopted | Argon2id with opaque revocable sessions and locally provisioned staff. Simplifies controlled demos, while recovery, MFA and organization scoping remain open. |
| ADR-004 Adopted | Separate check-in, receipt, incident and responder confirmation. Use persisted retry keys and a manual workflow. Confirmation has no real dispatch meaning. |
| ADR-005 Adopted | Authenticate SMS delivery with HMAC/freshness and deduplicate on gateway event ID. Keep sender and inferred location unverified; separate consent links from data reads. |
| ADR-006 Proposed | Advisory AI with verified read tools and deterministic validation before optimization. Select model/provider only after evaluation and privacy review. |
| ADR-007 Open | Choose incident/report cardinality migration, mission cancellation and reassignment semantics, and operator scope before expanding the workflow. |
| ADR-008 Open | Choose retention windows, audit event coverage, staged hosting/database TLS and SMS identity controls before wider access. |
| ADR-009 Open | Establish objective and fairness metric, graph provenance, and hospital resource freshness/eligibility policy before committing to solver behavior. |

New decisions record context, considered options, rationale, consequences, evidence, and status. Superseded entries point to replacements. See [Guardrails](GUARDRAILS.md) and [Roadmap](ROADMAP.md).
