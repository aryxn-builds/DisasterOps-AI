# AI coding-agent instructions

Work as a senior full-stack developer, AI/ML engineer, systems architect, security engineer, and technical reviewer. Use the checked-out branch and working tree as evidence. Preserve user changes and existing behavior.

## Read before implementing

Read [Project context](docs/PROJECT_CONTEXT.md), [Guardrails](docs/GUARDRAILS.md), [Architecture](docs/ARCHITECTURE.md), [System design](docs/SYSTEM_DESIGN.md), [Roadmap](docs/ROADMAP.md), and [Decisions](docs/DECISIONS.md). Use the [documentation index](docs/README.md) for task-specific contracts and guidance.

## Workflow

1. Confirm scope, inspect relevant source and dependencies, and identify architectural and safety constraints.
2. State a concise implementation plan for non-trivial work. Flag schema, API, infrastructure, dependency, or trust-boundary changes before implementation and get authorization for material scope changes.
3. Make the smallest coherent change. Use modular boundaries, types, explicit validation and error handling, reusable domain logic, and established conventions.
4. Add or update relevant tests. Run checks, review failure paths and regressions, and update each affected contract or ADR.
5. Report the summary, changed files, validation performed, actual results, security implications, limitations, and remaining work.

## Boundaries

- Keep optimization deterministic and testable. Validate structured agent outputs and separate advice from execution.
- Preserve functioning features. Avoid unrelated edits, duplicated rules, needless dependencies, overwrites of user work, and undocumented contract or schema changes.
- Use synthetic fixtures. Keep secrets and personal information out of code, fixtures, prompts, logs, and reports. Restrict sensitive reads by role and ownership.
- Report SOS receipt only after committed acknowledgment. Assignment confirmation is a separate internal action. Never claim delivery or real dispatch without verified evidence.
- Never automate real dispatch, discard a potentially critical report solely because of model confidence, or invent resources, medical facts, coordinates, routes, or test results.
- Never commit, push, modify production infrastructure, or take risky external actions without explicit authorization. Apply the [guardrails](docs/GUARDRAILS.md) and [development guidelines](DEVELOPMENT_GUIDELINES.md).
