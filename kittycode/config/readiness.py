from pathlib import Path
from typing import List, Dict

from kittycode.config.runtime import has_critical_failures, run_environment_checks


def run_readiness_checks(project_root: Path) -> List[Dict]:
    checks = []

    runtime_checks = run_environment_checks()
    checks.append(
        {
            "name": "Runtime critical checks",
            "ok": not has_critical_failures(runtime_checks),
            "detail": "doctor critical checks",
            "fix": "Run `kitty doctor` and resolve critical failures.",
        }
    )

    required_files = [
        "pyproject.toml",
        "README.md",
        "CHANGELOG.md",
        "docs/product-spec-v1.md",
        "docs/command-spec.md",
        "docs/non-goals.md",
        "docs/architecture.md",
        "docs/release-policy.md",
        "docs/release-checklist.md",
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
        "pytest.ini",
    ]

    for rel in required_files:
        p = project_root / rel
        checks.append(
            {
                "name": f"File exists: {rel}",
                "ok": p.exists(),
                "detail": str(p),
                "fix": f"Create missing file: {rel}",
            }
        )

    return checks


def readiness_ok(checks: List[Dict]) -> bool:
    return all(bool(c.get("ok")) for c in checks)
