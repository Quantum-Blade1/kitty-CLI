# KittyCode CLI — Full Project Audit

**Version audited:** `0.2.0`  
**Audit date:** 2026-04-18  
**Project path:** `c:\start`  
**Test result:** ✅ 25/25 passed (0 failures)

---

## 1. Executive Summary

KittyCode is a well-structured, local-first AI coding CLI written in Python. It features a layered architecture, serious security primitives, and production-grade observability. The codebase is thoughtfully designed for a solo/small-team project — the module boundaries are clean, the security pipeline is layered, and the telemetry is solid. That said, there are several real issues that need addressing before a production v1 release: raw API keys in `.env`, a critical singleton bug in `SandboxValidator`, missing logging setup call, an unchecked double-validation in `run_cmd`, and test coverage gaps in the most security-critical code paths.

---

## 2. Architecture Overview

```mermaid
graph TD
    CLI["kittycode/cli/app.py\n(Typer CLI + REPL)"]
    AGENT["kittycode/agent/kitty.py\n(KittyAgent)"]
    PLANNER["agent/planner.py\n(Scope → Queue)"]
    DEBATE["agent/debate.py\n(Builder→Critic loop)"]
    LLM["models/llm.py\n(LLMClient)"]
    ROUTER["models/router.py\n(ModelRouter)"]
    PROVIDERS["models/providers.py\n(Bytez / Gemini / OpenRouter)"]
    HEALTH["models/health.py\n(ModelHealthTracker)"]
    MEMORY["memory/manager.py\n(MemoryManager)"]
    ENGINE["tools/engine.py\n(ToolEngine)"]
    CRITIC["core/critic.py\n(SafetyCritic)"]
    SANDBOX["security/sandbox.py\n(SandboxValidator)"]
    POLICY["security/policy.py\n(cmd allowlist)"]
    STATS["utils/stats.py\n(StatsManager)"]
    TELEMETRY["telemetry/logger.py\n(StructuredLogger)"]

    CLI --> AGENT
    AGENT --> PLANNER
    AGENT --> DEBATE
    AGENT --> LLM
    LLM --> ROUTER
    LLM --> ENGINE
    ROUTER --> PROVIDERS
    ROUTER --> HEALTH
    DEBATE --> ROUTER
    DEBATE --> ENGINE
    ENGINE --> CRITIC
    ENGINE --> SANDBOX
    CRITIC --> SANDBOX
    CRITIC --> POLICY
    AGENT --> MEMORY
    ROUTER --> STATS
    CLI --> STATS
    CLI --> TELEMETRY
    ROUTER --> TELEMETRY
    ENGINE --> STATS
```

The data flow for a Code-mode task:  
`User input → CLI → KittyAgent → Planner (scope) → queue of tasks → DebateManager (Builder + Critic) → ToolEngine → SafetyCritic → SandboxValidator → fs/cmd execution → flush all state`

---

## 3. Module-by-Module Analysis

### 3.1 `kittycode/cli/app.py` (898 lines) — ⭐⭐⭐⭐
**Strengths:**
- Clean Typer command surface with JSON output mode on every command (`--json`).
- `observe_command()` decorator gives every CLI command automatic latency + failure tracking.
- Proper exit codes (`EXIT_OK=0`, `EXIT_RUNTIME_ERROR=1`, `EXIT_USAGE_ERROR=2`) — machine-readable and CI-friendly.
- Mode-aware system prompt updates (Chat vs Code vs Reasoning).
- Typewriter streaming for UX — nice touch.

**Issues:**
- `run_app()` calls `select_theme()` and `select_primary_model()` on **every** launch, even for returning users. This is annoying UX for a non-onboarding launch.
- `setup_logging()` is **never called** from the CLI entry point. The `StructuredLogger` infrastructure exists but `kitty.log` will never be written unless `setup_logging()` is invoked somewhere. This is a silent dead zone in observability.
- The REPL's `"model"` and `"stats"` inline commands bypass the `observe_command()` decorator — those interactions are invisible to metrics.
- `global kitty` mutable singleton — not a bug but makes testing harder.

---

### 3.2 `kittycode/agent/kitty.py` — ⭐⭐⭐⭐⭐
**Strengths:**
- Clean orchestration. Clear separation between Chat fast-path, planner queue, and debate loop.
- `flush_all()` batches all dirty writes to a single end-of-cycle disk sync. Replaces the original scatter-write pattern.
- Chat mode cognitive barrier: schema is filtered to only `mem` tool — no structural tools can be called in that mode.
- Plugin loading is deferred and isolated.

**Issues:**
- `debate_active` is set based on `total_plan_size > 3`, but this is set in `generate_plan()`. If `execute_next_step()` is called without a prior `generate_plan()` call (e.g. from `get_response()` fallback), `debate_active` defaults `False` silently.
- `_extract_content` is copy-pasted across `kitty.py` / `planner.py` / `debate.py` / `llm.py` — should be a shared utility.

---

### 3.3 `kittycode/agent/planner.py` — ⭐⭐⭐⭐
**Strengths:**
- YAML-as-JSON parser is clever — handles LLM output escaping flaws much better than `json.loads`.
- Windows path regex pre-processing heuristic (`C:\foo` → `C:\\foo`) is a real-world fix.
- Scope system (`Ask` vs `Project`) prevents unnecessary tool calls for conversational requests.
- Strategy context injection (last 5 reflections) gives the agent learnable memory.

**Issues:**
- `get_strategy_context()` injects all 5 strategies into every system prompt. With long strategy strings, this could silently inflate token counts significantly over time.
- `STRATEGY_FILE` is opened with plain `open()` without explicit encoding — can break on non-UTF-8 Windows locales.
- No max bound on `self.strategies` — the strategy log will grow unboundedly. A `[-50:]` slice before saving would prevent bloat.

---

### 3.4 `kittycode/agent/debate.py` — ⭐⭐⭐⭐
**Strengths:**
- Clean Builder → Critic → optional Revision loop.
- Single revision attempt (not infinite) — avoids runaway token spend.
- Malformed critic verdict defaults to PASS — prevents blocking.
- Critic error defaults to PASS with a log — doesn't brick the pipeline.

**Issues:**
- Critic sees only `clean_speech` (text after tool strip), not the actual tool calls that were executed. For safety review, the critic should see **what tools were actually called**, not just the narration.
- `previous_output[:500]` truncation in revision prompt may cut off critical context for complex tasks.

---

### 3.5 `kittycode/models/router.py` — ⭐⭐⭐⭐⭐
**Strengths:**
- True provider abstraction (Bytez, Gemini, OpenRouter) — swappable without touching routing logic.
- Adaptive routing: health-based chain reordering via `build_routing_chain()`.
- Latency threshold auto-demotion (session-scoped, not permanent).
- Low-confidence output detection triggers fallback (not just hard errors).
- Router decision log (last 100 entries, trimmed to prevent unbounded growth).
- Dirty-flag write-on-flush pattern — no writes mid-request.

**Issues:**
- Provider selection logic (`if provider_name == "google"`) is a string match hardcoded in the router body. Adding a new provider requires editing `router.py` — should be a registry/dispatch table.
- `load_preferences()` is called in `__init__` but its return value is discarded — the stored prefs are in `TASK_PREFERENCES` module-level global, so this is technically correct but looks like dead code.

---

### 3.6 `kittycode/models/providers.py` — ⭐⭐⭐
**Strengths:**
- Clean provider abstraction with `BaseProvider.run()` interface.
- `GeminiProvider` and `OpenRouterProvider` both degrade gracefully when keys are missing.
- `OpenRouterProvider` uses stdlib `urllib` — zero extra dependencies.

**Issues:**
- `GeminiProvider.run()` concatenates messages as a raw `[ROLE]\n{content}` string — this loses multi-turn context structure and is not the correct way to pass conversation history to the Gemini API. The API supports a structured `contents` list.
- `MockResult` class is defined inline in two separate providers — should be a shared dataclass.
- `OpenRouterProvider` has no timeout on `urlopen` — a hanging request will block the router indefinitely.
- Error messages from `OpenRouterProvider` swallow the HTTP response body, making API errors opaque.

---

### 3.7 `kittycode/models/health.py` — ⭐⭐⭐⭐⭐
- Excellent. Consecutive failure threshold, session demotion, composite health score (60% SR + 40% inverse latency). No issues. Dirty-flag flush pattern correctly implemented.

---

### 3.8 `kittycode/memory/manager.py` — ⭐⭐⭐⭐
**Strengths:**
- Dual-backend (FAISS vector + keyword fallback) with clean env-var gating.
- Graph-linked memory with BFS neighbor expansion.
- Legacy migration path from old flat `memory.json`.
- Category validation and normalization.
- Prune with category protection (identity + reflections survive).

**Issues:**
- `list_memories(limit=N)` slices with `self.metadata[-max(1, limit):]`. If `limit > len(metadata)`, this returns fewer than requested with no indication — could silently surprise callers.
- `_save_state()` is called on **every** `set_fact()` call, not on flush. This is inconsistent with the dirty-flag pattern used everywhere else. Under a plan with many steps, this could cause many disk writes per interaction.
- `get_facts()` returns only the last 10 entries, hardcoded. Used in `show_screen()` for the footer count — the count is correct but the method name `get_facts()` implies all facts.
- `_backend` remains `"unknown"` until a retrieval is triggered — calling `mm.backend` before any retrieval triggers `_ensure_ml_loaded()` as a side effect.

---

### 3.9 `kittycode/security/sandbox.py` — ⭐⭐⭐⭐⭐
**Strengths:**
- `resolve()` → `commonpath()` → symlink check is the correct 3-step defense. This is textbook path containment.
- Cross-platform: case-insensitive on Windows via `ntpath`, case-sensitive on Linux via `posixpath` — no manual hacks needed.
- Well-documented WHY this is safe (the docstring is genuinely good).

**🐛 Critical Bug:**
```python
def get_validator(root: Path = None) -> SandboxValidator:
    global _default_validator
    if _default_validator is None or root is not None:
        _default_validator = SandboxValidator(root)
    return _default_validator
```
`SafetyCritic.__init__` calls `get_validator(self.project_root)` passing an explicit root. This **replaces** the module-level singleton's root with whatever `project_root` the critic was instantiated with. If a second `ToolEngine` is created with a different root later (e.g. in tests or multi-project use), the singleton is quietly re-rooted. The singleton pattern and the `root=` override parameter are mutually exclusive design choices — pick one.

---

### 3.10 `kittycode/security/policy.py` — ⭐⭐⭐⭐
**Strengths:**
- Allowlist-first approach. Only explicitly permitted executables can run.
- Shell control token blocklist prevents chaining (`&&`, `||`, `;`, `|`, `>`, `` ` ``, `$()`).
- `BLOCKED_EXECUTABLES` blocks destructive system commands.
- Env-var customization (`KITTY_CMD_ALLOWLIST`) for power users.

**Issues:**
- `-c` is in `BLOCKED_ARG_PATTERNS`. This blocks `python -c "..."` (legitimate) AND `bash -c "..."` (dangerous). Since `bash`/`powershell` are already in `BLOCKED_EXECUTABLES`, the `-c` block is over-broad and may frustrate users trying to run quick Python one-liners.
- `shlex.split(cmd, posix=False)` on Windows is correct but `posix=False` means quotes are kept as part of the token — `exe = parts[0].lower()` may include quotes if a path is quoted, defeating the allowlist check.

---

### 3.11 `kittycode/core/critic.py` — ⭐⭐⭐⭐
**Strengths:**
- Deterministic rule-based gate — not LLM-based, cannot be hallucinated past.
- Prompt injection detection in write content (logs warning, allows — correct).
- Unexpected parameter check catches confused LLM tool calls.
- `review_batch()` for bulk validation.

**Issues:**
- `_check_path_safety` is called **after** `_check_write` / `_check_mkdir`. But `_check_write` and `_check_mkdir` both access `args["path"]` themselves. If path is missing from args, those specific checks won't error but the generic path check will also silently skip with no feedback.
- `_check_run_cmd` calls `validate_command()` from `policy.py`, but `ToolEngine.execute_tools()` also calls `_resolve_safe_path()` after `critic.review()`. For `run_cmd`, there is no `path` arg, so `_resolve_safe_path` is never called — correct. But the double-validation for `run_cmd` in both `action_run_cmd()` (in `fs_tools.py`) AND `_check_run_cmd` is redundant. If policy changes, you need to update two places.

---

### 3.12 `kittycode/tools/engine.py` — ⭐⭐⭐⭐
**Strengths:**
- SafetyCritic is lazily initialized to break circular imports.
- Destructive confirmation prompts pause the Rich spinner correctly.
- YAML parser fallback for malformed JSON tool arrays.
- Windows path escape heuristic.

**Issues:**
- `clean_speech` stripping is naive: `json_string.replace(json_str, "").replace("```json", "").replace("```", "")`. If the same JSON fragment appears twice in the response (e.g. model echoes the tool call in text), one occurrence stays.
- No timeout on tool execution — a `run_cmd` calling a long-running process will block the REPL indefinitely.

---

### 3.13 `kittycode/telemetry/logger.py` — ⭐⭐⭐⭐⭐
- Excellent design. Thread-local trace context, JSON formatter, structured kwargs API. The only gap is that `setup_logging()` is never called from the CLI entry point, so the file handler is never registered in production use.

---

### 3.14 `kittycode/utils/stats.py` — ⭐⭐⭐⭐⭐
- Clean singleton with dirty-flag flush. Per-model call count, per-command latency, failure tracking. No issues.

---

### 3.15 `kittycode/config/settings.py` — ⭐⭐⭐
**Issues:**
- `PROJECT_ROOT = Path.cwd()` — this is evaluated at **import time**, not at runtime. If the user's working directory changes after import (unlikely in CLI but possible in tests), the root is stale. A function `get_project_root()` would be safer.
- `KITTY_PROJECT_DIR.mkdir(exist_ok=True)` runs at module import time — creates `.kitty/` in whatever the CWD is when the module is first imported, including during test collection.
- Both `ENV_PATH` (`~/.kittycode/.env`) and `PROJECT_ROOT / ".env"` are loaded. Project-level `.env` overrides global. This is intentional but undocumented — worth a comment.

---

## 4. Security Audit

| Surface | Status | Notes |
|---|---|---|
| Path traversal | ✅ Blocked | `SandboxValidator` + `os.path.commonpath` |
| Symlink escape | ✅ Blocked | Pre-resolve + post-resolve check |
| Shell injection via chaining | ✅ Blocked | Token blocklist in `policy.py` |
| Dangerous executables | ✅ Blocked | `BLOCKED_EXECUTABLES` set |
| Dangerous file extensions | ✅ Blocked | `.exe .bat .ps1 .sh .dll .sys .vbs .cmd` |
| Sensitive paths (.env, .git) | ✅ Blocked | Regex patterns in `SafetyCritic` |
| Large write bomb | ✅ Blocked | 1 MB limit in `_check_write` |
| Deep directory creation | ✅ Blocked | 10-level depth limit |
| Prompt injection in write content | ⚠️ Logged only | Detected but not blocked |
| API keys in source | ✅ Clean | No hardcoded keys in source |
| **API keys in `.env` (committed)** | 🔴 **CRITICAL** | `.env` is in the repo root AND `.gitignore` only has `*.pyc` patterns — see below |
| Singleton sandbox root confusion | 🔴 Bug | `get_validator()` can be re-rooted by `SafetyCritic` |
| `run_cmd` timeout | ⚠️ Missing | Blocking subprocess with no limit |

---

## 5. 🔴 Critical: API Keys Exposed

Your `.env` file contains live API keys:
```
GEMINI_API_KEY=AIzaSyDXyF7xWkssVkgI8RuDLA9nizVKjJzIMA0
OPENROUTER_API_KEY=sk-or-v1-2686826...
```

Your `.gitignore` is:
```
__pycache__/
*.pyc
*.pyo
dist/
*.egg-info/
```

`.env` is **not in `.gitignore`**. If this repo has ever been pushed to a remote (GitHub, etc.), these keys are likely already exposed. **You should rotate both keys immediately** and add `.env` to `.gitignore`.

---

## 6. Test Coverage

**All 25 tests pass** (`pytest tests/ -q` → exit 0).

| Test File | What It Tests |
|---|---|
| `test_cli_contract.py` | CLI command surface, JSON output, exit codes |
| `test_cli_reliability.py` | error-path exit codes |
| `test_engine.py` | ToolEngine parse + dispatch |
| `test_memory.py` | MemoryManager core ops |
| `test_memory_cli.py` | CLI memory subcommands |
| `test_models_stage5.py` | registry, health, prefs |
| `test_observability_stage8.py` | StatsManager |
| `test_planner.py` | Planner scope + queue parsing |
| `test_security_policy.py` | command policy allowlist |
| `test_runtime_config.py` | RuntimeConfig singleton |
| `test_build_script_stage10.py` | build artifacts script |
| `test_packaging_stage9.py` | pyproject.toml packaging |
| `test_stage10_readiness.py` | release readiness gate |

**Gaps:**
- No tests for `SandboxValidator` (the most critical security component)
- No tests for `SafetyCritic` (path checks, write size limits, extension blocking)
- No tests for `DebateManager`
- No tests for `GeminiProvider` or `OpenRouterProvider`
- No tests for `MemoryManager` graph operations or pruning logic
- No test for `setup_logging()` being called at startup

---

## 7. Code Quality Issues

### Mixed line endings
Several files use `\r\n` (Windows CRLF) inside repos that also have `\n` files. Git will show false diffs. Add a `.gitattributes`:
```
* text=auto
*.py text eol=lf
```

### `_extract_content` copy-paste (4 locations)
`kitty.py`, `planner.py`, `debate.py`, `llm.py` all define the exact same helper function. Should be extracted to `kittycode/utils/helpers.py`.

### `requirements.txt` is incomplete
```
bytez
```
That's the entire file. The actual runtime deps are in `pyproject.toml` but `requirements.txt` is what the README tells users to install first. It's missing `rich`, `typer`, `pyyaml`, `numpy`, `python-dotenv`.

### `setup.py` is redundant
`setup.py` exists alongside `pyproject.toml`. Modern Python packaging needs only `pyproject.toml`. `setup.py` can be deleted.

### `memory_export_*.json` files in project root
There are 6 memory export files committed to the repo root. These are runtime artifacts and should be in `.gitignore`.

### `RuntimeConfig` missing `persona_enabled` in `__init__`
`RuntimeConfig.__new__` sets `strict_mode` and `theme` but `persona_enabled` is a `@property` derived from `strict_mode`. If `strict_mode` is somehow unset, `persona_enabled` will `AttributeError`. Safe but fragile.

---

## 8. Dependency Analysis

| Package | Used For | Risk |
|---|---|---|
| `typer` | CLI framework | ✅ Stable |
| `rich` | Terminal UI | ✅ Stable |
| `bytez` | Model provider | ⚠️ Unknown stability/SLA |
| `pyyaml` | JSON resilience parser | ✅ Stable |
| `numpy` | FAISS embeddings | ✅ Stable |
| `python-dotenv` | `.env` loading | ✅ Stable |
| `google-genai` | Gemini provider | ⚠️ Optional, not in requirements |
| `faiss-cpu` | Vector memory | ⚠️ Optional, not in requirements |
| `sentence-transformers` | Embeddings | ⚠️ Optional, not in requirements |

The optional deps (`google-genai`, `faiss-cpu`, `sentence-transformers`) are guarded by `try/except ImportError` — good. But they're not listed as optional extras in `pyproject.toml`, so users can't install them with `pip install kittycode[vector]`.

---

## 9. Prioritized Recommendations

### 🔴 Must Fix (Before Any Commit/Push)
1. **Rotate your Gemini and OpenRouter API keys immediately.** Add `.env` to `.gitignore`.
2. **Fix `get_validator()` singleton bug** — make it not re-rootable by `SafetyCritic` passing a custom root.

### 🟠 High Priority
3. **Call `setup_logging()` from the CLI entry point** — `app.py`'s `@app.callback()` or a `__main__` guard. Otherwise the log file is never written.
4. **Fix `requirements.txt`** — it should list all runtime deps that `pyproject.toml` declares.
5. **Add `SandboxValidator` and `SafetyCritic` to the test suite** — these are the most critical security components and have zero test coverage.
6. **Add `.env`, `memory_export_*.json`, `.kitty/`, `*.log` to `.gitignore`.**

### 🟡 Medium Priority
7. **Extract `_extract_content` to `kittycode/utils/helpers.py`** — remove 4 copies.
8. **Fix `GeminiProvider.run()`** — use the structured `contents` list API, not string concatenation.
9. **Add timeout to `OpenRouterProvider.urlopen()`** — e.g. `timeout=30`.
10. **Cap `strategies` list in `Planner`** before saving (e.g. `[-100:]`).
11. **Add optional deps to `pyproject.toml`** as `[project.optional-dependencies] vector = [...]`.
12. **Remove `setup.py`** — redundant with `pyproject.toml`.
13. **Add `.gitattributes`** for consistent line endings.

### 🟢 Nice to Have
14. **Don't call `select_theme()` and `select_primary_model()` on every launch** — only on first run or explicit `--setup` flag.
15. **Remove duplicate `run_cmd` validation** — either in `action_run_cmd` or in `_check_run_cmd`, not both.
16. **Add tool execution timeout** via `subprocess.Popen` with `communicate(timeout=N)`.
17. Cover `DebateManager`, providers, and memory graph ops in tests.

---

## 10. Overall Score

| Category | Score | Notes |
|---|---|---|
| Architecture | 9/10 | Clean layering, good separation of concerns |
| Security | 7/10 | Strong primitives, but sandbox singleton bug + no tests for security layer |
| Code quality | 7/10 | Some copy-paste, CRLF issues, redundant setup.py |
| Test coverage | 6/10 | 25 tests pass but critical paths untested |
| Observability | 8/10 | Great infrastructure, not wired up at startup |
| Documentation | 8/10 | README is accurate, docs/ is thorough |
| API key hygiene | 2/10 | Keys in repo `.env` with no gitignore protection |
| **Overall** | **7/10** | Solid foundation, a few critical fixes needed |
