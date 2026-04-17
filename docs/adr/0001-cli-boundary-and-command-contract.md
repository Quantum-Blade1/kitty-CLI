# ADR 0001: CLI Boundary and Command Contract

- Status: Accepted
- Date: 2026-03-08

## Context
The project had mixed entrypoints and inconsistent behavior across interactive and command execution paths.

## Decision
- Use `kittycode.cli.app:app` as canonical CLI entrypoint.
- Keep thin compatibility shim only for legacy launchers.
- Freeze v1 command surface as documented in `docs/command-spec.md`.
- Standardize non-zero exit codes for command failures.

## Consequences
- Packaging and runtime are simpler to reason about.
- Automation and scripting become reliable.
- New commands require contract updates before merge.

