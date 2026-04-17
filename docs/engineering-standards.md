# Engineering Standards v1

## Code Quality
- Python 3.12 compatible.
- Type hints required on public functions and class methods.
- Keep functions focused; avoid large multi-responsibility methods.
- No silent `except` for critical paths; log with context.

## Error Handling
- Raise clear exceptions internally.
- CLI should convert exceptions to concise actionable messages.
- Use explicit exit codes for command-level failures.

## Security
- No hardcoded secrets, tokens, or credentials.
- All file paths pass through sandbox validation.
- Destructive operations require explicit user confirmation.
- Prefer non-shell execution for subprocess actions where possible.

## Logging and Observability
- Use structured logging via telemetry wrapper.
- Include trace IDs for interactive cycles.
- Record model routing, tool execution, and major state transitions.

## Testing
- Unit tests must be deterministic and offline-safe by default.
- New bug fixes require regression tests.
- Critical modules target >= 85% coverage.

## Documentation
- New commands must update `docs/command-spec.md`.
- Architecture-impacting decisions require a new ADR file.
- User-facing behavior changes must update README examples.

## Review Checklist
1. Command behavior matches command spec.
2. Security checks applied for new tool or path logic.
3. Error cases and degraded mode behavior tested.
4. Logs include useful operational detail without leaking secrets.
5. Docs updated for any contract change.

