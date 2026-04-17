# Testing Strategy v1

## Test Pyramid
- Unit tests for core modules:
  - `memory`, `models`, `security`, `tools`
- CLI contract tests:
  - command availability
  - JSON output shape
  - exit code semantics
- Integration tests:
  - deterministic command flows without network dependency

## Reliability Rules
- Tests must be offline-safe by default.
- Every bug fix must include a regression test.
- Command failures must return explicit non-zero exit codes.

## CI Gates
- Compile check must pass (`python -m compileall -q .`)
- Test suite must pass.
- Coverage must remain above threshold (`>=80%` for `kittycode` package in CI).

## Non-Goals for v1 Testing
- No flaky network/provider integration tests in required CI path.
- No long-running load tests in pull-request workflow.
