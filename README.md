# DisasterOps-AI

DisasterOps-AI is the application for **Agentic AI-Driven Disaster Response and Emergency Resource Allocation**, a final-year engineering research project. The current prototype supports authenticated SOS intake and human-reviewed assignments. Use synthetic data in demonstrations. The project has no government or emergency-service connection.

| Status | Capabilities |
| --- | --- |
| Implemented | Citizen registration and authentication, revocable sessions, separate safety check-ins and SOS reports, operator review, dispatcher-created incidents and assignments, assigned-responder confirmation, PostgreSQL migrations, signed SMS intake, and optional consent-based location sharing. |
| Simulated | Hospital resource and distance examples. `registration.html` is an archived mockup, excluded from the served application. |
| Partially implemented | Find People has browser and SMS intake. Dynamic Map displays report locations. Rescue Prioritization has manual assignment and confirmation. |
| Planned | Live hospital data, satellite and drone ingestion, device discovery, AI-assisted verification, dynamic routing and optimization. |
| Not verified | Physical phone and SMS delivery, target-device offline behavior, and deployed operation. |

See [AUDIT.md](AUDIT.md) for the original architecture and security findings and the Phase 0 migration sequence.

Start at the [documentation index](docs/README.md) for [architecture](docs/ARCHITECTURE.md), [module specifications](docs/MODULE_SPECIFICATIONS.md), [API](docs/API_CONTRACTS.md), [database](docs/DATA_MODEL.md), [security](docs/SECURITY.md), [roadmap](docs/ROADMAP.md), and [deployment](docs/DEPLOYMENT.md). See [Contributing](CONTRIBUTING.md), [Testing strategy](TESTING_STRATEGY.md), and [Agent instructions](AGENTS.md) for development workflows.

## Run locally

Create a dedicated PostgreSQL database and a login with permission to create its application tables. Use Python 3.11 or newer and run these commands from the repository root.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Set `DATABASE_URL` in `.env` using your database credentials. Apply the migrations to a fresh database. The old `schema.sql` is a historical reference.

```powershell
python -m alembic upgrade head
python -m disasterops.provision dispatcher study_dispatcher
python -m disasterops.provision responder study_responder
python server.py
```

Open `http://127.0.0.1:8000` and register a citizen. The provisioner prompts for passwords without echoing them. Local HTTP is a loopback-only development setting. Use HTTPS and secure cookies for network access. FastAPI also exposes interactive endpoint documentation at `/docs`.

## Workflows and access

- **Citizen.** Authenticate with `POST /api/v1/auth/login` and keep the session cookie. Submit `POST /api/v1/citizen/sos` with a fresh UUID in `request_id`, plus optional coordinates and a message. Retry an uncertain submission with the same UUID and payload. The server returns `acknowledged` and a report ID after committing the report. A safety check-in is a separate write to `PUT /api/v1/citizen/safety`. Citizens can only read their own SOS history.
- **Dispatcher.** Review reports, including ones without a GPS fix. Open an incident for a report, then assign it to a provisioned responder. Each report can have one incident and each incident can have one assignment in Phase 0.
- **Responder.** View only assigned reports and their associated callback data. Confirm your assignment in the portal or with `POST /api/v1/rescue/assignments/{id}/confirm`. A confirmed assignment records a responder's action in this application.
- **Location consent.** A dispatcher can send a share request to an international-format callback number attached to a report. The recipient controls the single-use link, which expires after 30 minutes. Only the requesting dispatcher can read the result. A gateway acceptance is not proof of delivery.

Phone numbers and exact locations are restricted to the authorized workflows above. Callback numbers are unverified. The service worker caches the public shell, and the browser can remember the configured project SIM for the SMS composer. Operator telemetry is excluded from that cache. The map uses external Leaflet assets pinned by integrity checks and OpenStreetMap base tiles. The application does not put report data into tile URLs.

## Optional Android SMS gateway

Configure the project's dedicated SIM and Android gateway signing key in `.env`. Register `/api/v1/sms/gateway/webhook` for the `sms:received` event using the gateway's own configuration. The receiver checks the HMAC over the raw body and signed timestamp and deduplicates by gateway event ID in PostgreSQL. Treat incoming SMS as unverified reports, even if the sender gives an account name. Reports without usable coordinates remain in the queue. Configure the outbound gateway URL and credentials only if testing consent links.
[Android SMS Gateway webhook documentation](https://docs.sms-gate.app/features/webhooks/)

Opening the offline SMS composer drafts a message. The sender must press Send in their SMS app. A signed gateway event is required for the backend to receive an SMS. Gateway retries return a duplicate acknowledgment without creating another report.

## Tests and maintenance

```powershell
python -m pytest -q
node --check app.js
node --check sw.js
```

The default suite exercises the API with SQLite in memory. To exercise the same workflows on PostgreSQL, set `TEST_DATABASE_URL` to a dedicated test database whose login can create schemas. The suite runs Alembic in a temporary schema and includes a concurrent webhook replay test.

```powershell
$env:TEST_DATABASE_URL = 'postgresql://testuser:replace-with-password@127.0.0.1:5432/disasterops_test'
python -m pytest -q
```

`server.py` is the entry point. `disasterops/routers` defines the HTTP boundaries, `services` handles application logic, and `schemas.py` and `models.py` define request validation and persistence. Keep migration revisions in `migrations/versions`. Use `frontend.css` and this command to regenerate the checked-in stylesheet after changing classes in templates or script.

```powershell
npx tailwindcss@3.4.17 -i frontend.css -o styles.css --content './{index.html,app.js}' --minify
```

Phase 0 is intended for controlled research use. Public exposure needs infrastructure rate limits for authentication and ingestion, a retention policy for sensitive records, database backup and restore procedures, and end-to-end testing with the intended Android gateway and phones. Keep access logs and error monitoring free of request bodies and share tokens.

working member - Kehshav and Aryan