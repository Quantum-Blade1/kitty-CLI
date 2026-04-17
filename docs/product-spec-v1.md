# KittyCode Product Spec v1

## One-Line User Promise
KittyCode is a reliable local-first AI coding CLI that helps developers analyze, plan, and execute project tasks safely with transparent memory and model routing.

## Target Users
- Solo developers building software locally.
- Indie hackers shipping quickly with minimal tooling overhead.
- Learners who want guided code help without losing control of files/commands.

## Primary Problems Solved
- Turning vague coding requests into actionable plans.
- Running controlled project operations from CLI with safety confirmation.
- Preserving useful project/user context across sessions.
- Handling model failures with fallback routing instead of hard stops.

## v1 Scope (Locked)
### In scope
- Production-ready CLI runtime with stable commands and help.
- Local structured memory store with offline-safe retrieval fallback.
- Multi-model routing with health checks and fallback chain.
- Tool execution engine with sandboxed path validation and confirmation gates.
- Observability basics: stats, diagnostics, and structured logs.
- Deterministic tests for core flows (offline-capable CI).

### Out of scope for v1
- Cloud sync or hosted backend.
- GUI/web dashboard.
- Team collaboration/multi-user workspaces.
- Marketplace-grade plugin ecosystem.
- Autonomous long-running background agents.

## Product Principles
- Safety first: no silent destructive execution.
- Local-first: must work in degraded/offline mode where possible.
- Transparency: explain model routing, memory usage, and tool actions.
- Operator control: user can inspect and override important behavior.
- Reliability over novelty: predictable behavior beats flashy behavior.

## Success Metrics (v1)
- Task success rate: >= 85% on curated local project workflows.
- CLI startup reliability: >= 99% successful startup in test matrix.
- Test pass rate: 100% on protected branch CI.
- Critical incident rate: 0 known secret leaks / 0 known sandbox escapes.
- Time to diagnose setup issues: <= 3 minutes using `kitty doctor`.

## v1 Acceptance Criteria
1. CLI installs and runs via `pip install -e .` and `kitty --help`.
2. Core commands produce stable output and non-zero exit codes on failure.
3. Missing API key does not crash CLI startup; degraded mode is explicit.
4. Memory operations remain functional without external model downloads.
5. Model router performs fallback when primary model fails.
6. Unsafe paths (`..`, cross-root) are blocked for file tools.
7. Destructive actions require explicit confirmation.
8. `doctor` reports actionable diagnostics and clear pass/fail checks.
9. Core modules have deterministic tests and CI coverage target.
10. No hardcoded credentials or secret defaults exist in source.

