# Project context

**Project:** Agentic AI-Driven Disaster Response and Emergency Resource Allocation. **Application:** DisasterOps-AI. **Type:** final-year engineering research project.

During disruptions, reports can arrive late, repeat, lack location, or conflict with changing transport and capacity information. The project studies how to preserve raw distress signals and help operators make traceable decisions with incomplete data. Use cases include a simulated flood response, a connectivity outage with SMS intake, and a road closure after a candidate route is generated. The intended users are citizens, dispatchers, responders, future hospital inventory staff, and research evaluators. They need different access, evidence, and acknowledgment semantics.

The original SOS prototype relied on process memory and simulated coordination. The current working tree adds a modular backend and human-confirmed assignment. Agentic interpretation, geospatial routing, computer vision, event processing, and operations research remain research directions. Study feasibility, uncertainty, timeliness and allocation fairness on controlled scenarios. Real emergency dispatch, medical advice, government integration, and operational claims are outside scope.

## Working-tree inventory and gaps

The documentation baseline is local branch `new-branch`, tracking `origin/new-branch` in the personal fork `aryxn-builds/DisasterOps-AI`. HEAD was `5de8a3c`; the modular foundation was present as working-tree changes, including untracked modules, migrations and tests. Use the local tree for this inventory. The remote was identified from Git configuration.

| Surface | Evidence and gap |
| --- | --- |
| Entry point and dependencies | [server.py](../server.py), [app factory](../disasterops/main.py), [dependencies](../requirements.txt), [settings](../disasterops/config.py). FastAPI/Uvicorn, Pydantic, SQLAlchemy, Alembic, pg8000, Argon2 and HTTPX. No checked-in container, CI or deployment manifest. |
| Frontend | [index.html](../index.html), [app.js](../app.js), [service worker](../sw.js), [share page](../share_location.html). Vanilla JS and checked-in Tailwind CSS, browser geolocation and motion, pinned Leaflet and external map tiles. Archived [registration mockup](../registration.html) is excluded from the active flow. |
| Persistence and tests | [models](../disasterops/models.py), [migration](../migrations/versions/0001_phase0.py), [tests](../tests/test_workflows.py). Legacy [schema.sql](../schema.sql) is reference material. Default SQLite checks do not exercise PostgreSQL locking or migration behavior. |
| Existing documentation | [README](../README.md) owns setup, [Audit](../AUDIT.md) preserves the original failure analysis, [MODULES](../MODULES.md) retains prior research notes. The new docs provide contracts and component ownership. |

## Capability status

| Label | Current disposition |
| --- | --- |
| **IMPLEMENTED** | Citizen auth and revocation in `routers/auth.py`; SOS and check-ins in `routers/citizen.py`; dispatcher and responder workflow in `routers/rescue.py`; PostgreSQL revision and scoped location consent endpoints. |
| **PARTIALLY IMPLEMENTED** | Find People has browser and SMS intake but no verified identity, expiry engine, mesh or image feeds. Dynamic Map has a Leaflet report view, with no route calculation. Rescue Prioritization has manual assignment without a solver or mission lifecycle. |
| **SIMULATED / MOCKED** | Hospital Enquiry uses `app.js:HOSPITALS`; inventory, distance, and availability values are synthetic. Historical OTP and onboarding UI are mockups. |
| **PLANNED** | Evidence-based Report Verification, incident clustering, authenticated hospital inventory, graph-based routing, constrained optimization, and AI-assisted coordination. See [five modules](MODULE_SPECIFICATIONS.md). |
| **NOT VERIFIED** | Physical SMS delivery, actual carrier behavior, offline capture on target phones, external tile availability, and deployment under load. Inbound HMAC and replay have automated tests. Outbound consent transport is stubbed in the test suite. |

No check-in implies unknown, not danger. The browser fix and phone are unverified. The prototype assumes a trusted research operator group, synchronized SMS timestamps, and a controlled PostgreSQL database. Current debt includes broad dispatcher visibility, absent lifecycle and retention jobs, no distributed throttling, per-report workflow queries, and no operational SLO measurements. See [Security](SECURITY.md), [Decisions](DECISIONS.md), and [Glossary](GLOSSARY.md).
