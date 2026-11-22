# Security architecture and threat assessment

## Trust boundaries and controls

Citizens, operator browsers, SMS senders, signed gateways, PostgreSQL and future agents have distinct trust. A signed webhook authenticates the gateway and protects payload integrity, while SMS identity and coordinates remain unverified. Treat report text and future media as hostile input. A malicious or compromised dispatcher has a wider data scope than a citizen.

| Actor | Current permissions |
| --- | --- |
| Anonymous | Public shell/config, registration, login. Cannot read reports or assignments. |
| Citizen | Own account view, SOS receipt/history and own safety write. Cannot claim media or gateway identities. |
| Dispatcher | Global research report queue with callback/coordinates, incident creation and assignment. Only own consent results. |
| Responder | Assigned rows and associated report details; can confirm own assignment. |
| Gateway/link holder | Signed SMS write or token-limited location submission, respectively. Neither grants data reads. |

[Auth service](../disasterops/services/auth.py) uses Argon2id, random opaque tokens, hashed storage, absolute expiry, and logout revocation. Default sessions last 28,800 seconds. Cookie is HttpOnly and SameSite Strict, Secure by default, with explicit HTTP loopback development exception. Middleware suppresses validation echoes, omits raw paths in structured API logs, sets security headers, and blocks disallowed mutation origins. [SMS service](../disasterops/services/sms.py) verifies HMAC-SHA256 over raw body plus Unix timestamp in constant time, with a ±300-second window. [SMS router](../disasterops/routers/sms.py) fails closed when no signing key is configured. Database uniqueness protects accepted event IDs across processes. [Consent router](../disasterops/routers/location.py) uses digests, expiry and a one-time conditional write.

## Current risk register

| Severity | Finding | Before broader use |
| --- | --- | --- |
| High | No application or checked-in edge throttling. Public Argon2 operations and intake could exhaust CPU or database capacity. | Set measured request/body limits and separate budgets for login, registration and intake. Alert on bursts without silently losing acknowledged reports. |
| High | All dispatchers can see all reports and callbacks. No organizational scoping, MFA or sensitive-read audit. | Define tenant/incident access rules, staff MFA/recovery, and audit privileged reads. |
| High | No retention/purge process, backup policy or deployed database encryption controls in this repo. | Approve retention, restrict exports, require protected backups, least-privilege DB credentials, TLS and restore drills. |
| Medium | Callback ownership is unverified; consent sends lack idempotency or quotas. Gateway accepts an operator-configured URL. | Restrict eligible destinations/egress, require HTTPS in staging and bound consent requests. Treat acceptance as distinct from delivery. |
| Medium | Location results remain readable to requester after link expiry if submitted. No audit of access. | Set a separate results retention policy and log access. |
| Medium | Inline scripts permitted by CSP; CDN, tile service and transitive dependencies remain dependencies. | Tighten CSP, assess tile privacy/legal constraints and run dependency review. |
| Medium | Operational logs describe HTTP outcomes, with no durable audit trail for views or review decisions. | Add protected append-only records and useful alerts without coordinates, SMS text, passwords, or tokens. |

## Future attack surfaces

Files have no upload route today. Before adding one, require size/type limits, quarantine, isolated storage, malware checks, metadata minimization, authorization and signed access. AI tools have no executable runtime today. Treat instructions embedded in documents, SMS or images as data, grant scoped read tools, validate output and tool arguments, and forbid arbitrary network/SQL, privileged writes and dispatch. Freeform reports can contain personal or medical data. Minimize access and retention, particularly before sharing them with an external provider.

## Incident response

Capture request IDs, timestamps and affected privileges in a restricted channel. Contain exposure by disabling the affected gateway or endpoint and revoking sessions/credentials with approved operator access. Preserve protected evidence and assess scope, data exposure and report loss. Repair and test with synthetic data. Restore from verified backups or reconcile explicitly before reopening, and document notification decisions under the applicable policy. See [Guardrails](GUARDRAILS.md), [Deployment](DEPLOYMENT.md), and [Tests](../TESTING_STRATEGY.md).
