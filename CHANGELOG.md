# Changelog

All notable changes to this project will be documented in this file.

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
