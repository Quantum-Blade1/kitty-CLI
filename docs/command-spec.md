# KittyCode Command Spec v1

## Contract Rules
- Every command must support `--help`.
- Failures must return non-zero exit codes.
- Error messages must be human-readable and action-oriented.
- No command should require network access unless explicitly documented.

## Command Surface (Frozen for v1)

## `kitty`
Purpose: Interactive assistant session for chat/code workflows.

Behavior:
- Starts REPL.
- Supports mode switching (`Chat`, `Code`, `About`).
- In `Code` mode, may plan and request confirmation before execution.

Exit codes:
- `0` normal exit.
- `1` runtime failure.

## `kitty doctor`
Purpose: Local environment diagnostics.

Behavior:
- Checks required runtime conditions (env vars, dirs, key deps).
- Prints pass/fail per check.
- Returns non-zero if critical checks fail.

Exit codes:
- `0` all critical checks pass.
- `2` one or more critical checks fail.

## `kitty models`
Purpose: Inspect model registry/routing health.

Behavior:
- Lists models, provider, health, success rate, avg latency.
- Shows current routing strategy.
- Supports preference controls:
- `--set-primary <model>`
- `--reset`
- `--persist/--no-persist`
- `--show-chain <Code|Chat|Thought>`

Exit codes:
- `0` success.
- `1` unexpected runtime error.

## `kitty models --set-primary <model_key>`
Purpose: Set active primary model for current session.

Behavior:
- Validates model key exists in registry.
- Updates task routing preference in memory/session.

Exit codes:
- `0` model set.
- `2` invalid model key.

## `kitty memory [--limit <n>] [--category <name>]`
Purpose: Inspect structured memory entries (default memory action).

## `kitty memory add --key <k> --value <v> [--category <name>]`
Purpose: Add structured memory entries.

## `kitty memory find "<query>" [--limit <n>]`
Purpose: Search semantic/keyword memory context.

## `kitty memory prune [--max <n>] [--dedupe/--no-dedupe]`
Purpose: Memory hygiene operation for pruning and deduplication.

## `kitty memory export [--path <file>]`
Purpose: Export full memory payload for backup or analysis.

## `kitty stats`
Purpose: Show observability metrics.

Behavior:
- Displays model usage, health, planner/tool metrics, and memory size.

Exit codes:
- `0` success.
- `1` runtime read error.

## `kitty chat "<message>"`
Purpose: One-shot chat response without entering REPL.

## `kitty run "<task>"`
Purpose: One-shot plan generation for code tasks.

Variants:
- `kitty run "<task>" --execute --yes` executes the queue non-interactively.

## `kitty config [--set-theme <theme>]`
Purpose: Show and update runtime CLI configuration.

## `kitty version`
Purpose: Print installed CLI version.

## `kitty readiness`
Purpose: Execute v1 release-readiness gate checks and return readiness status.

## Global Flags
- `--strict`: deterministic low-flair behavior.
- `--debug`: verbose structured logs.
- `--json`: machine-readable output for command endpoints.

## Output Format (v1)
- Human-readable rich output is the default.
- JSON output mode is supported for command endpoints via `--json`.
