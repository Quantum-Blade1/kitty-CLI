# ADR 0002: Memory Backend Strategy (Vector + Offline Fallback)

- Status: Accepted
- Date: 2026-03-08

## Context
Vector memory dependencies may be unavailable in user environments, causing startup/runtime failures.

## Decision
- Keep structured memory metadata as the source of record.
- Use vector retrieval when local model/index stack is available.
- Automatically fall back to keyword retrieval when unavailable.
- Never block core CLI behavior on vector backend initialization.

## Consequences
- Improved reliability in constrained or offline environments.
- Slight retrieval quality reduction in fallback mode is acceptable for v1.
- Test suite can run deterministically without network/model downloads.

