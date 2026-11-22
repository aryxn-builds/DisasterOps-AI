# Requirements and acceptance

Goals are durable intake, honest status, least-privilege coordination and reproducible research. Citizens need clear receipt and failure states. Dispatchers need evidence and safe decisions. Responders need scoped and actionable assignments. Hospital staff and evaluators need traceable inventory and experiments.

| ID | Requirement and acceptance | Ownership / phase |
| --- | --- | --- |
| FR-001 | Authenticate citizens and provision distinct operator roles. Reject unauthorized reads and writes. | Foundation / 1 |
| FR-002 | Accept valid SOS with or without GPS and issue a receipt only after commit. Verify same-key retry returns the original receipt. | M1 / 2 |
| FR-003 | Separate check-in from distress. Verify SAFE cannot cancel an SOS. Label absent and stale check-ins unconfirmed. | M1 / 2 |
| FR-004 | Review every accepted report; retain evidence through outage and low confidence. Record reviewer action. | M5 / 3 |
| FR-005 | Only dispatcher opens and assigns an incident, and only assigned responder confirms. Test cross-role and cross-object denial. | M4 / 1, 8 |
| FR-006 | Publish timestamped facility inventories and reservations with specialty guards. Test concurrent reservation and stale data. | M2 / 5 |
| FR-007 | Record simulation mission states and resolution, with approved changes and notification status distinct from assignment. | M4 / 8 |
| NFR-001 | Fail requests explicitly on DB loss and recover from backup. Verify no false acknowledgment and perform restore drill. | Foundation / 1, 10 |
| NFR-002 | Measure receipt latency, query load and completeness under replay. Agree on a documented budget after baseline collection. | All / 9 |
| SEC-001 | Hash passwords, revoke sessions, isolate contacts/coordinates, redact logging and demonstrate denied object access. | Foundation / 1 |
| SEC-002 | Reject stale/invalid signatures and persist replay protection under concurrency. | M1 / 2 |
| SEC-003 | Define retention, staff MFA/recovery, operator scopes, audit and edge abuse controls before broader exposure. | Foundation / 10 |
| GEO-001 | Version road graph and hazard overlays; reject routes using invalid edges and report unreachable destinations. | M3 / 4 |
| OPT-001 | Explain unmet demand and reject allocations violating capacity, reachability, suitability or shifts. | M4 / 6 |
| AI-001 | Use scoped tools and validated outputs. Demonstrate no unsupported numbers or autonomous writes under injection and outage fixtures. | M2, M5 / 7 |
| REP-001 | Publish reproducible baseline protocol with seeds, inputs, metrics and uncertainty; separate simulations and real observations. | Research / 9 |

Phase numbers refer to the [roadmap](ROADMAP.md). Criteria describe requirements, so a row may include future work even if a subset already has tests. See [Module specifications](MODULE_SPECIFICATIONS.md).
