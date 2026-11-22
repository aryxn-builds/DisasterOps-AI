# Implementation roadmap

Sequencing starts with the local foundation. These phases describe development gates, with no dates or completion percentages. The historical audit calls its foundation change Phase 0; here that work contributes evidence to phases 0–2 and the manual workflow portion of phase 8.

| Phase | Objective, prerequisites and tasks | Deliverable, tests and definition of done | Risk and current status |
| --- | --- | --- | --- |
| 0 Audit and documentation | Inspect checked-out tree and map implementation, proposals and tests. | Source-backed docs and reproducible baseline; validate links, diagrams and traceability. | Historically conflated proposals and features. Audit and docs exist. |
| 1 Secure backend | Require phase 0 baseline. Keep modular boundaries, secure sessions and migrations, review authorization gaps. | Repeatable clean DB and role/ownership tests; resolve staff scope and readiness criteria before staging. | Core implemented; lifecycle/abuse controls remain. |
| 2 Reliable intake | Depends on 1. Verify browser, GPS loss, signed SMS, replay and independent check-ins. Add device failure/evidence handling. | Retry and concurrent webhook tests plus device/offline test matrix and honest status UX. | Core implemented; physical gateway and phone matrix unverified. |
| 3 Verification and incidents | Depends on 2. Add evidence records, review state, incident links and explicit resolution. | Review queue retains all reports; regression tests for outages, duplicates and reviewer actions. | Manual incident creation exists, evidence workflow planned. |
| 4 Routing | Depends on source/licensing decisions and phase 3 evidence boundaries. Import versioned graph, validate closures, calculate routes. | Route fixture tests for direction, closure, accuracy and unreachable states. | Leaflet report map exists; routing planned. |
| 5 Hospital resources | Depends on 1 and scoped staff policy. Model facility suitability, freshness and reservation. | Concurrent inventory/reservation tests and stale-data exclusion. | Current data simulated. |
| 6 Optimization | Depends on 3–5. Define objective, constraints, infeasibility and baselines. | Validated candidate plans with versioned inputs and reference fixtures; demonstrate no invalid allocations. | Planned; data quality and fairness risks. |
| 7 Agent integration | Depends on safe contracts and deterministic baseline. Add bounded LangGraph workflows and typed tools. | Injection, outages and structured output tests; human review and deterministic fallback demonstrated. | Planned; grounding and model/provider variability risks. |
| 8 Operations UX | Depends on relevant verified services. Add review evidence, hospital/admin UX, simulated missions and approved replanning. | Role-specific browser scenarios, accessibility and failure/reload behavior checked. | Manual assignment exists; lifecycle and roles expansion planned. |
| 9 Evaluation | Depends on stable scenarios and solver/agent contracts. Run frozen comparative protocol. | Reproducible runs and metrics with limitations, workload, seeds and uncertainty. | No research results claimed; sampling bias risk. |
| 10 Deployment and demo | Depends on scoped security, restore, evaluation and approval. Stage synthetic scenario and prepare runbooks. | Documented test environment, rollback and verified demo, with deployment review. | No checked-in Docker/CI or production verification. |

Next gate: validate SOS retry and acknowledgment behavior on actual target phones and an isolated SMS gateway, while defining abuse-control and operator access requirements. See [Requirements](REQUIREMENTS.md), [Deployment](DEPLOYMENT.md), and [Future research](FUTURE_PHASES.md).
