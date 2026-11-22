# Phase 0 architecture and security audit

Baseline: initial commit `5de8a3c`. This audit describes the prototype before the Phase 0 changes.

| Surface | What the prototype actually does | Finding |
| --- | --- | --- |
| `server.py` | Serves pages and accepts registration, location, SOS, SMS and map requests. Writes to seeded process memory. | Public identity spoofing and personal data reads; plaintext passwords; fixed rescue token; no effective authorization; loss on restart. |
| SMS and location sharing | Parses SMS coordinates, can call a configured Android gateway, serves a browser consent page. | Signature bypass when unconfigured, unsigned simulator enabled by default, memory-only replay tracking, user-controlled gateway destination, unbound personal data lookup and reusable share tokens. Incoming SMS logs contain personal data. |
| `index.html` | Renders citizen controls, shake detection, SMS composer, Leaflet map and hospital cards. | Browser-minted identities, local storage of sensitive data, unsafe rendering of server data, optimistic success, fabricated coordinates and dispatch messages. Hospital capacity is synthetic. |
| `registration.html` | Standalone staged mockup with fake OTP and identity fields. | No verified registration or identity check. Unnecessary sensitive-data prompts for a prototype. |
| `share_location.html`, `sw.js` | Browser geolocation consent and offline shell caching. | Share token in query string, unauthenticated result lookup and broad cache policy. |
| `schema.sql`, environment and dependencies | Unused PostgreSQL DDL and configuration placeholders. | No runtime database driver, migration runner, persistence or automated tests. |
| `README.md`, `MODULES.md` | Product walkthrough and research design. | No evidence of government integration, device discovery, live hospital capacity, satellite/drone ingestion, AI verification, routing solver or real dispatch. |

## Migration plan

1. Introduce a new versioned PostgreSQL schema, configure explicitly and fail closed. Keep the historical SQL as a reference. Use a fresh database for Phase 0. Back up and reconcile any independently populated legacy database before migration. Never import bundled fixtures, demo sessions or plaintext passwords.
2. Separate accounts and revocable sessions, citizen check-ins, SOS reports, incidents, and assignments. Use Argon2id, operator-provisioned dispatcher and responder roles, owner-only citizen reads, and assignment-scoped responder reads.
3. Acknowledge SOS only after a durable write. Accept missing GPS. Make browser retries idempotent. Require dispatcher incident and assignment actions followed by confirmation by the assigned responder.
4. Verify Android gateway requests from raw bytes using the documented timestamp and HMAC format. Store provider event IDs atomically with intake. Preserve coordinate-free and unverified messages for human review. Scope optional location requests to reports, with a single-use consent token separate from the authenticated result.
5. Keep the existing interface and local device features where they can use the secure contracts. Hide historical demo credentials and identity collection, label synthetic data, and remove background geo tracking and fake dispatch claims.
6. Verify auth, isolation, retries, assignment transitions, consent, signed SMS and migrations before documenting test results. Keep this work on the current branch.

The historical application used only process memory. There is no durable operational dataset in the repository to backfill.
