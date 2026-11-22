# Architecture

This document owns component structure. See [System design](SYSTEM_DESIGN.md) for behavior and [Deployment](DEPLOYMENT.md) for runbooks.

## Current system context

```mermaid
flowchart LR
  C[Citizen browser] --> App[FastAPI research application]
  D[Dispatcher browser] --> App
  R[Responder browser] --> App
  G[Optional Android gateway] -->|Signed inbound webhook| App
  App -->|Optional consent SMS request| G
  App --> DB[(PostgreSQL)]
```

`server.py` hosts the modular monolith. [create_app](../disasterops/main.py) initializes the SQLAlchemy engine, serves same-origin HTML and assets, mounts API routers, and applies response headers and redacted logging. The service worker caches the public shell. Leaflet and base tiles are external browser resources. Gateway configuration and physical integration are optional.

```mermaid
flowchart TD
  Entry[server.py] --> App[App factory and HTTP middleware]
  App --> Pages[HTML JS CSS service worker]
  App --> Routes[Auth citizen rescue SMS and location routers]
  Routes --> Contracts[Pydantic request schemas]
  Routes --> Services[Auth reports and SMS services]
  Routes --> DBSession[Request-scoped SQLAlchemy session]
  Services --> DBSession
  DBSession --> Models[SQLAlchemy models]
  Models --> DB[(PostgreSQL)]
  Migration[Alembic revision] --> DB
```

The backend imports no browser code. Routers enforce roles, validate requests, and compose use cases. Services hold reusable session, report, and transport logic. Legacy `schema.sql` is excluded from the active migration path. Some operator workflows and persistence queries remain directly in routers.

## Current SOS flow

```mermaid
flowchart LR
  Web[Authenticated browser] --> Validate[Validate account and request UUID]
  SMS[Gateway] --> Sign[Check signature timestamp and event ID]
  Validate --> Commit[Commit report]
  Sign --> Commit
  Commit --> Receipt[Return acknowledgment]
  Commit --> Review[Dispatcher review]
  Review --> Incident[Open incident and assign responder]
  Incident --> Confirm[Assigned responder confirms]
```

**Synchronous.** Browser API requests, database transactions, gateway webhook receipt, and the outbound consent-link request/response. The gateway accepts requests separately from carrier delivery. **Asynchronous in the current system.** Browser geolocation, service worker caching, carrier transport and independent inbound deliveries. Operators can refresh the queue and check consent status on demand. There is no durable job queue or scheduled dispatch worker.

## Proposed component architecture

```mermaid
flowchart TD
  UI[Citizen PWA and operator interfaces] --> API[FastAPI and authorization]
  HospUI[Hospital staff portal] --> API
  API --> Ingress[Report ingestion]
  API --> Capacity[Hospital services]
  API --> Mission[Mission and policy services]
  Ingress --> Store[(PostgreSQL and PostGIS)]
  Capacity --> Store
  Mission --> Store
  Ingress --> Outbox[Transactional outbox]
  Outbox --> Verify[Verification workers]
  Verify --> Agents[Advisory AI orchestration]
  Capacity --> Planner[Deterministic optimizer]
  Geo[Versioned graph and routing] --> Planner
  Agents --> Planner
  Planner --> Mission
  Mission --> Audit[Protected audit records]
  Gateways[Approved external gateways] --> Ingress
```

The citizen PWA handles authenticated submission, drafts and check-ins. Operations and responder interfaces surface evidence, approvals and assignment progress. The hospital portal scopes inventory writes to a facility. PostGIS would store versioned spatial evidence. Workers consume durable events and emit review context. Approved adapters isolate provider failures. Keep the monolith until evidence justifies a deployment split.

## Proposed advisory flow and planning

```mermaid
flowchart LR
  E[Evidence snapshot] --> I[Incident intelligence]
  E --> H[Hospital enquiry]
  I --> C[Rescue coordinator]
  H --> C
  C --> P[Validate structured inputs]
  P --> Solver[Deterministic solver]
  Solver --> Review[Human review]
```

```mermaid
flowchart LR
  A[Operator-approved demands] --> S[Freeze versioned snapshots]
  S --> M[Route matrix and capacity constraints]
  M --> O[Solve under time budget]
  O --> F[Check path capacity and policy feasibility]
  F --> P[Publish candidate and unmet demand]
  P --> H[Operator approval required]
```

```mermaid
flowchart LR
  Event[Material closure or capacity change] --> V[Check affected plans and versions]
  V --> R[Recompute affected routes]
  R --> Candidate[New candidate with differences]
  Candidate --> Review[Operator decision]
  Review --> History[Record approval or rejection]
```

## Deployment structure

```mermaid
flowchart LR
  Local[Local browser] --> U[Current loopback Uvicorn]
  U --> DB[(Local PostgreSQL)]
  Test[Proposed staging users] --> Edge[HTTPS proxy and rate limits]
  Edge --> App[FastAPI web replicas]
  App --> StageDB[(Private PostgreSQL and optional PostGIS)]
  StageDB --> Worker[Proposed background workers]
  App --> Obs[Redacted monitoring]
  Worker --> Obs
```

In the target, reads and acknowledged writes remain synchronous. Durable verification and replanning would run asynchronously using event IDs, aggregate versions and retry policies. See [AI design](AI_AGENT_DESIGN.md) and [Data model](DATA_MODEL.md).
