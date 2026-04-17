# Release Readiness v1

This document defines the production release gate for v1.

## Gate Criteria
1. Runtime diagnostics have no critical failures (`kitty doctor`).
2. Test suite passes in CI.
3. Coverage gate passes (>=80% package coverage).
4. Packaging artifacts build successfully.
5. Core documentation and release policy files exist.
6. Command contract and changelog are present.

## Operational Gate
- Run:
  - `kitty readiness`
  - or `kitty --json readiness` for machine-readable output.
- Exit code `0` means ready.
- Exit code `2` means one or more gate checks failed.

## Release Decision Rule
If readiness fails, release is blocked until all failed checks are resolved.
