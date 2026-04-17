# ADR 0003: Model Routing and Fallback Policy

- Status: Accepted
- Date: 2026-03-08

## Context
Single-model dependence creates brittle failures and poor user experience during provider outages or latency spikes.

## Decision
- Route by task type (`Chat`, `Code`, `Thought`) with primary + fallback chain.
- Track per-model health and latency during session and across persisted stats.
- Deprioritize models with repeated failure or excessive latency.
- Expose health and routing visibility via CLI (`kitty models`, `kitty stats`, logs).

## Consequences
- Higher response reliability.
- Slight complexity increase in routing logic.
- Easier operational diagnosis and performance tuning.

