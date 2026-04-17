# ADR 0004: Model Provider Abstraction and Preference Persistence

- Status: Accepted
- Date: 2026-03-08

## Context
Router logic previously mixed provider SDK calls, routing policy, and preference state, making extension and testing harder.

## Decision
- Introduce provider abstraction layer (`models/providers.py`) with a `BaseProvider` contract and `BytezProvider` implementation.
- Move routing-chain calculation into `models/policy.py`.
- Add persistent model preference management in `models/preferences.py`, stored at `.kitty/model_preferences.json`.
- Expose preference controls via CLI (`models --set-primary`, `--reset`, `--persist`, `--show-chain`).

## Consequences
- Cleaner separation of concerns in model stack.
- Easier future support for non-Bytez providers.
- Stable, user-visible routing preferences across sessions/projects.
