# API contracts

Current endpoints are mounted by [create_app](../disasterops/main.py). Request types live in [schemas.py](../disasterops/schemas.py). All paths below are relative to `/api/v1` unless specified. Authenticated calls use the `disasterops_session` cookie. Never place it in URLs or JavaScript storage.

## Common behavior

Mutations from browsers use the exact configured origin when an `Origin` header is present. The middleware rejects cross-origin or cross-site mutation requests with 403. API responses are marked `no-store`, and errors use `{"detail":"…"}` for handled cases. Missing/invalid session is 401, wrong role is 403, and protected object searches can return 404. Pydantic validation gives a redacted 422. SQLAlchemy failures are handled as 503. All paths may include a server-generated `X-Request-ID` response header.

Usernames are trimmed and lowercased, 3–40 characters, with ASCII letters, numbers, underscores or hyphens. Passwords are 12–128 characters for registration and 1–128 for login. Phones use `+` and 7–15 digits without a leading zero. Coordinates are finite, latitude ±90 and longitude ±180, with optional accuracy 0–100,000 metres. UUID fields must validate as UUIDs. First-party request schemas forbid extra fields.

## Auth and public configuration

| Method and path | Actor and request | Success and side effects | Specific errors and retry behavior |
| --- | --- | --- | --- |
| POST /auth/register | Public. username, password, optional phone | 201 `{username}`. Creates citizen with Argon2id hash | 409 username unavailable. Repeats do not return the original success. |
| POST /auth/login | Public. username, password | 204, sets HttpOnly session cookie. Creates session and prunes expired rows | 401 invalid credentials. Each success issues a fresh token. |
| GET /auth/me | Any session | 200 `{username,role,safety_status,safety_updated_at}`; safety fields nullable | Read only. |
| POST /auth/logout | Cookie optional, no body | 204. Deletes current token digest if present and clears cookie | Repeatable. |
| GET /config | Public | 200 `{gateway_number}`, nullable project SIM | Read only. |

Sources: [auth router](../disasterops/routers/auth.py), [auth service](../disasterops/services/auth.py).

## Citizens, incidents and assignments

`Report` contains `id, source, received_at, latitude, longitude, accuracy_meters, battery_percentage, message`. The latter five values can be null. For dispatcher or assigned responder views it additionally exposes nullable `phone`. `Assignment` contains `id, incident_id, status, confirmed_at`; status is `PENDING` or `CONFIRMED`, and timestamp is nullable. `Workflow` adds nullable `incident_id` and nullable `assignment`. List routes take `offset` ≥ 0, default 0, and return at most 50 records.

| Method and path | Actor and request | Success and side effects | Specific errors and retry behavior |
| --- | --- | --- | --- |
| PUT /citizen/safety | Citizen. status SAFE or NEEDS_HELP | 200 `{status,updated_at}`. Updates own row | Repeat refreshes timestamp. |
| POST /citizen/sos | Citizen. request_id, source BUTTON (default) or SHAKE_DEVICE, optional paired coordinates and accuracy, battery 0–100, message max 2,000 chars | 201 `{status:"acknowledged",report_id,received_at}` after commit | Repeat same UUID/payload returns same acknowledgment. 409 if payload differs. Accuracy requires a coordinate pair. |
| GET /citizen/sos | Citizen. optional offset | 200 list of own Report + Workflow | Read only. |
| GET /citizen/sos/{report_id} | Citizen owner | 200 Report + Workflow | 404 for missing or other citizen's report. |
| GET /rescue/reports | Dispatcher. optional offset | 200 list of Report with phone + Workflow + nullable location_request_id for that dispatcher | Read only. |
| POST /rescue/incidents | Dispatcher. report_id | 201 `{id,report_id}`. Opens incident | 404 report absent, 409 existing incident. |
| POST /rescue/incidents/{incident_id}/assignments | Dispatcher. responder_username | 201 Assignment, pending | 404 unknown incident or responder, 409 already assigned. |
| GET /rescue/assignments | Responder. optional offset | 200 list of own Assignment + nested Report with phone | Read only. |
| POST /rescue/assignments/{assignment_id}/confirm | Assigned responder. no body | 200 Assignment, confirmed | 404 missing or unassigned. Repeat preserves timestamp. |

Sources: [citizen](../disasterops/routers/citizen.py), [rescue](../disasterops/routers/rescue.py), [serializers and transactions](../disasterops/services/reports.py).

## Gateway and consent

| Method and path | Actor and request | Success and side effects | Specific errors and retry behavior |
| --- | --- | --- | --- |
| POST /sms/gateway/webhook | Signed gateway. Raw event with id 1–128 chars, event sms:received, payload containing message 1–12,000 chars and optional sender/phoneNumber up to 32 chars | 200 `{status:"acknowledged"}` after commit or `{status:"duplicate_ignored"}` for previously recorded ID | 503 disabled, 413 over 32,768 bytes, 401 invalid/stale signature, 400 invalid signed payload. |
| POST /locate/request | Dispatcher. report_id | 201 `{request_id,status}`, status accepted_by_gateway or delivery_unconfirmed. Commits link issuance then calls gateway. | 404 report absent, 409 no eligible callback, 503 outbound disabled. Each retry can issue a new SMS. |
| POST /locate/submit | Single-use link holder. 43-character URL-safe token, latitude, longitude, optional accuracy_meters | 200 `{status:"received"}`. Stores consented location | 404 invalid, expired (30 minutes) or used token. Repeats consume no additional write. |
| GET /locate/status/{request_id} | Dispatcher who created request | 200 status PENDING, EXPIRED or LOCATED. Located adds latitude, longitude, accuracy_meters, submitted_at | 404 missing or wrong owner. |

See [SMS router](../disasterops/routers/sms.py) and [location router](../disasterops/routers/location.py). Static GET routes serve `/`, `/app.js`, `/styles.css`, `/sw.js`, and `/share-location`. `/registration` and `/registration.html` redirect to the main form. FastAPI provides `/docs`, `/redoc` and `/openapi.json` with its default configuration.

## Planned boundaries

Design interfaces only after requirements and authorization are approved. Auth and citizen management need lifecycle, consent and recovery. SOS and incidents need versioned membership, review and resolution. Verification requires evidence append and reviewer decisions. Hospital and team/resource contracts require scoped inventory and reservations. Map contracts publish versioned snapshots and route feasibility. Allocation publishes candidate plans, missions enforce approval/acknowledgment, notifications expose delivery separately from receipt, and analytics use deidentified aggregates. See [Roadmap](ROADMAP.md) and [Data model](DATA_MODEL.md).
