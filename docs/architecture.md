# KittyCode Architecture v1

## Goals
- Provide a stable production CLI with clear operational boundaries.
- Keep runtime local-first, safe-by-default, and debuggable.
- Ensure every major subsystem is replaceable behind explicit interfaces.

## High-Level Modules
- `kittycode/cli`: command entrypoints, user interaction, rendering, exit codes.
- `kittycode/agent`: orchestration logic (plan, execute, reflect).
- `kittycode/models`: provider abstraction, routing, health tracking.
- `kittycode/memory`: structured memory store and retrieval backends.
- `kittycode/tools`: tool registry and tool execution runtime.
- `kittycode/security`: sandbox and policy validation.
- `kittycode/telemetry`: structured logs, trace context, metrics.
- `kittycode/config`: runtime config, environment and path settings.

## Layering Rules
1. `cli` can depend on all lower layers.
2. `agent` can depend on `models`, `memory`, `tools`, `telemetry`, `config`.
3. `tools` can depend on `security`, `telemetry`, `config`.
4. `models` and `memory` must not import `cli`.
5. `security` must not depend on `cli`, `agent`, or provider SDKs.
6. `config` must be side-effect minimal and import-safe.

## Data Flow
1. User invokes a CLI command.
2. CLI resolves config and validates environment.
3. Agent decides mode:
- Chat: direct response flow.
- Code: planner queue + optional tool execution.
4. Model router selects model chain and executes with fallback.
5. Tool engine parses/validates actions, asks confirmation for destructive operations.
6. Memory stores facts and context with vector-or-keyword retrieval.
7. Telemetry records trace logs and metrics.

## Runtime Modes
- `strict`: deterministic behavior (lower temperature, minimal persona).
- `default`: assistant persona with professional execution gates.
- `debug`: verbose structured logs to terminal + file.

## Critical Interfaces

## `ModelRouter`
- Input: prompt payload + task type.
- Output: `(result, model_key)` or explicit exception.
- Guarantees:
- fallback chain attempted in deterministic order.
- health and latency tracked.

## `MemoryManager`
- Input: facts/messages/query.
- Output: persisted entries and relevant context list.
- Guarantees:
- no hard crash when vector backend unavailable.
- local metadata remains readable/writable.

## `ToolEngine`
- Input: LLM text containing tool payload.
- Output: `(actions_taken, clean_speech)`.
- Guarantees:
- safety critic gate executes pre-tool call.
- path validation enforced by `SandboxValidator`.
- destructive tools require explicit confirmation.

## Safety Model
- Single source of truth for path containment: `security/sandbox.py`.
- Tool execution is deny-by-default on validation failures.
- No hardcoded credentials in repository.

## State and Storage
- Global config: `~/.kittycode/.env`
- Project state: `<project>/.kitty/`
- Current files:
- `memory_meta.json`
- `stats.json`
- `model_health.json`
- `router_log.json`
- `model_preferences.json`
- `kitty.log`

## Error Handling Strategy
- User-facing CLI errors are concise and actionable.
- Internal exceptions are logged with structured metadata.
- Known recoverable failures degrade gracefully:
- missing API key
- unavailable model/provider
- unavailable vector backend

## Test Strategy Alignment
- Unit tests for parser/sandbox/router/memory.
- Integration tests for command flows and exit code contract.
- Offline-safe tests by default; no network dependency in CI.

## Future Evolution (post-v1)
- JSON output contracts for all commands.
- Persistent config command set.
- Policy-driven command allowlist profiles.
