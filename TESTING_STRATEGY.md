# Testing and evaluation strategy

Separate feature validation from research experiments. The suite in [tests/test_workflows.py](tests/test_workflows.py) covers password hashing and sessions, denied role and object access, receipt/retry/check-in semantics, manual assignment ownership, webhook validity and replay, consent-link isolation and expiry, and storage failure without acknowledgment.

## Current checks

Run `python -m pytest -q` for the SQLite-backed API suite. Set `TEST_DATABASE_URL` to an isolated PostgreSQL database for migration parity and concurrent replay checks. The [fixture](tests/conftest.py) creates and removes a unique test schema. Run `node --check app.js` and `node --check sw.js` for script syntax. Browser, physical SMS and deployment tests require a suitable environment; report them individually with evidence. No evaluation dataset or completed experimental comparison is checked in.

## Planned test layers

| Layer | Check |
| --- | --- |
| Unit | Coordinate and role validation, parser boundaries, TTL, stale rules and deterministic ranking. |
| API and security | Invalid schemas, unauthenticated and cross-role calls, ID guessing, origin checks, auth expiry, signature/replay, rate-limit and log redaction. |
| Persistence | Migration from empty and representative prior versions, rollback/restore, competing writes and scoped constraints on PostgreSQL. |
| SOS and deduplication | Missing GPS, uncertain POST then retry, malformed/stale SMS, events arriving concurrently, many reports about one incident without dropping original reports. |
| Routing and replanning | Direction, closures, unreachable routes, version changes, only affected candidate plans recalculated, approved actions protected. |
| Optimization | Infeasible demand, hard capacity/time constraints, suitability, deterministic fixture comparisons and adversarial boundary values. |
| Agents | Schema failures, injected instructions, forbidden tools, missing data, stale values, unsupported numeric claims and deterministic/manual fallback. |
| End-to-end simulation | Synthetic citizen, dispatcher, responder and hospital actors through outages and replanning, with explicit simulated outcomes and no external dispatch. |

## Comparative protocol

Compare first-come-first-served, nearest-incident-first (route time), severity-first (operator-defined categories), optimization-only, and agent-assisted optimization. Use the same seeded incidents, shifts, capacity, route snapshots, time budgets and eligibility rules. Use stable tie-breaking. Keep versions, failed runs, workload settings and timeout handling. Pair runs by scenario and report uncertainty as sample size permits.

- Receipt rate = uniquely acknowledged reports divided by valid submitted reports, with uncertain receipts and failures counted separately. Replay suppression = repeated accepted event keys without additional rows divided by attempts to replay accepted keys.
- Response delay = simulated arrival time minus report receipt time in minutes; report median and tail percentiles alongside the count of unserved cases. Service coverage = fulfilled eligible demand divided by eligible demand.
- Utilization = committed eligible resource time divided by available resource time. Report hard-constraint violations, infeasibility, solve latency and solver status.
- Equity = report the largest gap in service coverage between defined zones, with counts and eligibility caveats. Explain any proxy outcomes and avoid real-world survival inference.
- Agent quality = supported extracted fields divided by cited extracted fields, unsupported claim frequency, reviewer overrides, false negatives on critical items and validation fallback rate. Declare denominators and report empty or uncertain cases separately.

See [Requirements](docs/REQUIREMENTS.md) and [AI design](docs/AI_AGENT_DESIGN.md).
