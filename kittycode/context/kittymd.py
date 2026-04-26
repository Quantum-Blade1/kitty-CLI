"""
KITTY.md — Project context loader and template generator.

Every production coding CLI reads the project before the first user turn.
KITTY.md is KittyCode's equivalent of Claude's CLAUDE.md or Cursor's
.cursorrules: a markdown file at the project root that tells the agent
what this project is, how to build/test it, and what conventions to follow.
"""

import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MAX_KITTYMD_CHARS = 4000


# ─────────────────────────────────────────────────────────────────
# Loader
# ─────────────────────────────────────────────────────────────────

def load_kittymd(project_root: Path) -> str:
    """
    Load KITTY.md from *project_root* if it exists.

    Search order:
        1. ``<project_root>/KITTY.md``
        2. ``<project_root>/.kitty/KITTY.md``

    Returns the file contents (capped at 4 000 chars) or an empty string
    if neither location exists.
    """
    candidates = [
        project_root / "KITTY.md",
        project_root / ".kitty" / "KITTY.md",
    ]

    for path in candidates:
        if path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
                if len(content) > MAX_KITTYMD_CHARS:
                    content = (
                        content[:MAX_KITTYMD_CHARS]
                        + f"\n\n[...truncated — KITTY.md exceeds {MAX_KITTYMD_CHARS} chars]"
                    )
                logger.info("Loaded KITTY.md from %s (%d chars)", path, len(content))
                return content
            except Exception as e:
                logger.warning("Failed to read %s: %s", path, e)
                return ""

    return ""


# ─────────────────────────────────────────────────────────────────
# Template generator
# ─────────────────────────────────────────────────────────────────

def _detect_project_name(root: Path) -> str:
    """Try to extract a project name from common config files."""
    # pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8")
            m = re.search(r'name\s*=\s*"([^"]+)"', text)
            if m:
                return m.group(1)
        except Exception:
            pass

    # package.json
    pkg_json = root / "package.json"
    if pkg_json.is_file():
        try:
            import json
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            if "name" in data:
                return data["name"]
        except Exception:
            pass

    # Cargo.toml
    cargo = root / "Cargo.toml"
    if cargo.is_file():
        try:
            text = cargo.read_text(encoding="utf-8")
            m = re.search(r'name\s*=\s*"([^"]+)"', text)
            if m:
                return m.group(1)
        except Exception:
            pass

    # Fallback to directory name
    return root.name


def _detect_language(root: Path) -> str:
    """Best-effort language detection from config files."""
    if (root / "pyproject.toml").is_file() or (root / "setup.py").is_file():
        return "Python"
    if (root / "package.json").is_file():
        return "JavaScript / TypeScript"
    if (root / "Cargo.toml").is_file():
        return "Rust"
    if (root / "go.mod").is_file():
        return "Go"
    if (root / "pom.xml").is_file() or (root / "build.gradle").is_file():
        return "Java"
    return "Unknown"


def _detect_test_runner(root: Path) -> str:
    """Detect the test command from config files."""
    # Python — pytest
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8")
            if "pytest" in text:
                return "pytest"
        except Exception:
            pass
    if (root / "pytest.ini").is_file() or (root / "setup.cfg").is_file():
        return "pytest"

    # JS/TS — jest / vitest
    pkg_json = root / "package.json"
    if pkg_json.is_file():
        try:
            import json
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            scripts = data.get("scripts", {})
            test_cmd = scripts.get("test", "")
            if "jest" in test_cmd:
                return "jest"
            if "vitest" in test_cmd:
                return "vitest"
            if test_cmd:
                return f"npm test ({test_cmd})"
        except Exception:
            pass

    # Rust
    if (root / "Cargo.toml").is_file():
        return "cargo test"

    # Go
    if (root / "go.mod").is_file():
        return "go test ./..."

    return "unknown"


def _detect_linter(root: Path) -> str:
    """Detect linter from config files."""
    # Python — ruff / flake8 / pylint
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8")
            if "ruff" in text:
                return "ruff"
            if "flake8" in text:
                return "flake8"
        except Exception:
            pass
    if (root / "ruff.toml").is_file() or (root / ".ruff.toml").is_file():
        return "ruff"

    # JS/TS — eslint
    for name in (".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yml"):
        if (root / name).is_file():
            return "eslint"

    # Rust
    if (root / "Cargo.toml").is_file():
        return "clippy (cargo clippy)"

    return "none detected"


def _detect_vcs(root: Path) -> str:
    """Detect version control."""
    if (root / ".git").exists():
        return "git"
    if (root / ".hg").exists():
        return "mercurial"
    return "none detected"


def _detect_dependencies(root: Path) -> list[str]:
    """Extract top-level dependency names."""
    deps = []

    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8")
            # Find the dependencies = [...] block and extract package names
            dep_match = re.search(r'dependencies\s*=\s*\[(.*?)\]', text, re.DOTALL)
            if dep_match:
                dep_block = dep_match.group(1)
                for m in re.finditer(r'"([a-zA-Z0-9][a-zA-Z0-9_.-]*)', dep_block):
                    name = re.split(r'[><=!~\[;]', m.group(1))[0].strip()
                    if name and name not in ("python",) and len(name) > 1:
                        deps.append(name)
        except Exception:
            pass

    pkg_json = root / "package.json"
    if pkg_json.is_file():
        try:
            import json
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            for section in ("dependencies", "devDependencies"):
                deps.extend(data.get(section, {}).keys())
        except Exception:
            pass

    # Deduplicate, keep order, cap at 20
    seen = set()
    unique = []
    for d in deps:
        if d not in seen:
            seen.add(d)
            unique.append(d)
    return unique[:20]


def generate_kittymd_template(project_root: Path) -> str:
    """
    Generate a starter KITTY.md based on project detection.

    Reads pyproject.toml / package.json / Cargo.toml for project name + deps.
    Detects test runner, linter, and VCS.

    Returns the markdown content string — does NOT write to disk.
    """
    name = _detect_project_name(project_root)
    lang = _detect_language(project_root)
    test_runner = _detect_test_runner(project_root)
    linter = _detect_linter(project_root)
    vcs = _detect_vcs(project_root)
    deps = _detect_dependencies(project_root)

    deps_block = ""
    if deps:
        deps_list = ", ".join(f"`{d}`" for d in deps[:15])
        if len(deps) > 15:
            deps_list += f", ... (+{len(deps) - 15} more)"
        deps_block = f"\n**Key Dependencies**: {deps_list}\n"

    template = f"""# {name}

> This file tells Kitty about your project. Edit it to match your workflow.

## Project Overview

- **Language**: {lang}
- **Test Runner**: `{test_runner}`
- **Linter**: `{linter}`
- **VCS**: {vcs}
{deps_block}
## Build & Test

```bash
# Run all tests
{test_runner}

# Lint
{linter if linter != 'none detected' else '# (add your lint command here)'}
```

## Coding Conventions

- Follow the existing code style in this project.
- Write tests for every new feature or bugfix.
- Keep functions small and focused.
- Add docstrings to all public functions and classes.

## Project Structure

<!-- Describe key directories and their purpose -->

## Important Notes

<!-- Add anything Kitty should know: API keys patterns, deploy process, etc. -->
"""
    return template
