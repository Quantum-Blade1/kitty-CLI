# KittyCode v1 Non-Goals

This document prevents scope creep during v1.

## Explicit Non-Goals
- Building a web app or desktop GUI.
- Multi-user collaboration and shared state sync.
- Remote hosted memory/model backend.
- Billing/subscription/account systems.
- Full plugin marketplace and trust/signing infrastructure.
- Autonomous unattended long-running workflows.
- Voice input/output interfaces.
- Mobile clients.
- Fine-tuning pipelines and training infrastructure.
- Complex workflow DSL/orchestration language.

## Deferred Improvements (Post-v1)
- `--json` output mode for all commands.
- Persistent model profile presets across projects.
- Rich config management command set (`kitty config ...`).
- Plugin permission audit UI.
- Session export/import and replay tooling.

## Guardrails for Feature Requests
A feature should be rejected from v1 if it:
- Requires new external infrastructure.
- Adds major security surface without strong tests.
- Delays stabilization of the current command contract.
- Reduces determinism or makes debugging harder.

## Rule
If a request is outside this scope, capture it in a backlog doc and continue v1 stabilization first.

