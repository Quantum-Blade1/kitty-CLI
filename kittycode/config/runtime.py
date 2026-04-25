from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import List

from kittycode.config.settings import BYTEZ_KEY, OPENROUTER_KEY, KITTY_GLOBAL_DIR, KITTY_PROJECT_DIR, PROJECT_ROOT


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    severity: str  # "critical" | "warning"
    detail: str
    fix: str


@dataclass(frozen=True)
class RuntimeEnvironment:
    project_root: Path
    project_state_dir: Path
    global_config_dir: Path
    bytez_key_present: bool


def get_runtime_environment() -> RuntimeEnvironment:
    return RuntimeEnvironment(
        project_root=PROJECT_ROOT,
        project_state_dir=KITTY_PROJECT_DIR,
        global_config_dir=KITTY_GLOBAL_DIR,
        bytez_key_present=bool(BYTEZ_KEY),
    )


def run_environment_checks() -> List[CheckResult]:
    env = get_runtime_environment()
    checks: List[CheckResult] = [
        CheckResult(
            name="Project root exists",
            ok=env.project_root.exists(),
            severity="critical",
            detail=str(env.project_root),
            fix="Run from a valid project directory.",
        ),
        CheckResult(
            name="Project state dir exists (.kitty)",
            ok=env.project_state_dir.exists(),
            severity="critical",
            detail=str(env.project_state_dir),
            fix="Re-run kitty in this project or create .kitty directory.",
        ),
        CheckResult(
            name="Global config dir exists (~/.kittycode)",
            ok=env.global_config_dir.exists(),
            severity="warning",
            detail=str(env.global_config_dir),
            fix="Create ~/.kittycode for stable global config.",
        ),
        CheckResult(
            name="BYTEZ_API_KEY configured",
            ok=env.bytez_key_present,
            severity="warning",
            detail="Present" if env.bytez_key_present else "Missing",
            fix="Set BYTEZ_API_KEY in ~/.kittycode/.env for model calls.",
        ),
        CheckResult(
            name="bytez installed",
            ok=find_spec("bytez") is not None,
            severity="warning",
            detail="Python package import check",
            fix="Optional provider: pip install bytez to enable Bytez models",
        ),
        CheckResult(
            name="yaml installed",
            ok=find_spec("yaml") is not None,
            severity="critical",
            detail="Python package import check",
            fix="Install dependencies: pip install -r requirements.txt",
        ),
        CheckResult(
            name="numpy installed",
            ok=find_spec("numpy") is not None,
            severity="critical",
            detail="Python package import check",
            fix="Install dependencies: pip install -r requirements.txt",
        ),
        CheckResult(
            name="OPENROUTER_API_KEY or BYTEZ_API_KEY configured",
            ok=bool(OPENROUTER_KEY or BYTEZ_KEY),
            severity="critical",
            detail="At least one model provider key required",
            fix="Set OPENROUTER_API_KEY or BYTEZ_API_KEY in ~/.kittycode/.env",
        ),
        CheckResult(
            name="google-genai installed (optional)",
            ok=find_spec("google.genai") is not None,
            severity="warning",
            detail="Needed for Gemini models",
            fix="pip install google-genai",
        ),
    ]
    return checks


def has_critical_failures(checks: List[CheckResult]) -> bool:
    return any((not c.ok and c.severity == "critical") for c in checks)

