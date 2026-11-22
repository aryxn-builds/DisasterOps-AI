# Development guidelines

Use [AGENTS.md](AGENTS.md) for agent workflow and [Guardrails](docs/GUARDRAILS.md) for project policy.

- Python uses snake_case modules and functions, PascalCase schema/model classes, typed inputs and explicit transactions. Keep routers focused on HTTP and reuse domain services. Ruff can check or format affected Python when installed.
- The browser currently uses vanilla JavaScript. Keep DOM text safe, handle rejected requests and stale async responses, use named camelCase functions, and avoid browser storage for private data. If TypeScript is later approved, use strict checking, explicit boundary types and runtime validation. No TypeScript toolchain is required today.
- Keep root files for entry points and public assets, application modules under `disasterops/`, migrations under `migrations/`, tests under `tests/` and long-form guidance under `docs/`. Use short, descriptive file names.
- Work from a clearly identified feature/development branch. Preserve existing edits. If authorized to commit, use descriptive changes such as `docs: document SOS receipt contract`. Keep each commit and PR reviewable.
- Review dependencies for purpose, license, transitive risk and compatibility. Record changes to runtime requirements, environment variables and database contracts. Put safe examples in `.env.example`; secrets belong in ignored local configuration or a secret store.
- Log structured outcomes and correlation IDs. Catch expected failures at the boundary, preserve explicit validation/denial/conflict semantics, and avoid exposing exception internals. Retain safe reproducers with synthetic data.

## Pull request checklist and definition of done

Explain scope and user-visible behavior. Include tests for critical success and failure paths, PostgreSQL migration evidence where applicable, rollback or recovery considerations, and relevant security/privacy review. Update owning docs and add an ADR for a lasting design decision. Run validation described in [Testing strategy](TESTING_STRATEGY.md) and report actual results and remaining limits. Reviewers should check authorization, consistency, retry semantics, accessibility for UI work, and unrelated diff. See [Contributing](CONTRIBUTING.md).
