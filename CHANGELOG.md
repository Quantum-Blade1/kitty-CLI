# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-04-26

### Added
- **Quantum-Inspired Architecture**: Implemented pure-Python probabilistic heuristics.
  - Model Router (`router_q.py`): Superposition states and phase interference for routing.
  - Task Planner (`planner_q.py`): Quantum annealing-inspired algorithm to minimize task sequencing risk.
  - Memory Manager (`memory_q.py`): Grover-style amplitude amplification for $O(\sqrt{N})$ token matching pre-filtering.
- **Production Hardening**: Offline-safe initialization block inside `KittyAgent` to support memory-only operations without API keys.
- **Security & Sandboxing**: `SandboxValidator` now fully restricts traversals outside project directories (`../`); added robust test coverage for `SafetyCritic` policies.
- **Dependency Management**: Shifted completely to PEP 517 `pyproject.toml` with optional installation brackets (`[vector]`, `[gemini]`, `[all]`).
- **Telemetry**: Wired structured `setup_logging` natively to CLI entry points.

### Changed
- Removed deprecated `setup.py`.
- Modernized the `README.md` to reflect the new architecture.

### Fixed
- Fixed headless execution `stdin` hanging with CLI prompts during tests.
- Fixed tokenization/matching bug within `find_memory_entries`.
- Corrected engine policy list to properly allow valid `python -c` flag execution.


## [0.2.0] - 2026-03-08

### Added
- Production CLI command surface with JSON output support.
- Structured memory subcommands (`add`, `find`, `prune`, `export`).
- Model preference persistence and chain introspection.
- Command execution security policy and run command hardening.
- Command-level observability metrics and remediation-aware diagnostics.
- CI and release automation workflows.

### Changed
- Default memory backend policy to `keyword` for reliability on constrained systems.
- Router refactor with provider abstraction and routing policy separation.

### Fixed
- Legacy launcher compatibility import issue.
- Multiple CLI stability and encoding issues on Windows terminals.
