"""Tests for kittycode/context/kittymd.py"""

import pytest
from kittycode.context.kittymd import load_kittymd, generate_kittymd_template


def test_loads_kittymd(tmp_path):
    """load_kittymd should return the file contents when KITTY.md exists."""
    content = "# My Project\n\nThis is the project context.\n"
    (tmp_path / "KITTY.md").write_text(content, encoding="utf-8")

    result = load_kittymd(tmp_path)

    assert result == content
    assert "My Project" in result


def test_loads_kittymd_from_dotkitty_fallback(tmp_path):
    """load_kittymd should fall back to .kitty/KITTY.md when root file is absent."""
    dotkit = tmp_path / ".kitty"
    dotkit.mkdir()
    content = "# Fallback Context\n"
    (dotkit / "KITTY.md").write_text(content, encoding="utf-8")

    result = load_kittymd(tmp_path)

    assert "Fallback Context" in result


def test_missing_kittymd_returns_empty(tmp_path):
    """load_kittymd should return '' when neither KITTY.md location exists."""
    result = load_kittymd(tmp_path)

    assert result == ""


def test_kittymd_truncation(tmp_path):
    """load_kittymd should truncate files longer than 4000 chars."""
    long_content = "x" * 5000
    (tmp_path / "KITTY.md").write_text(long_content, encoding="utf-8")

    result = load_kittymd(tmp_path)

    assert len(result) < 5000
    assert "truncated" in result


def test_generate_template_detects_pytest(tmp_path):
    """generate_kittymd_template should detect pytest from pyproject.toml."""
    pyproject_content = '''
[build-system]
requires = ["setuptools"]

[project]
name = "awesome-project"
dependencies = ["requests", "click"]

[tool.pytest.ini_options]
testpaths = ["tests"]
'''
    (tmp_path / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")

    result = generate_kittymd_template(tmp_path)

    assert "pytest" in result
    assert "awesome-project" in result


def test_generate_template_detects_git(tmp_path):
    """generate_kittymd_template should detect git VCS."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n', encoding="utf-8")

    result = generate_kittymd_template(tmp_path)

    assert "git" in result


def test_generate_template_detects_npm(tmp_path):
    """generate_kittymd_template should handle package.json projects."""
    import json
    pkg = {
        "name": "my-app",
        "scripts": {"test": "jest"},
        "dependencies": {"react": "^18.0.0"},
    }
    (tmp_path / "package.json").write_text(json.dumps(pkg), encoding="utf-8")

    result = generate_kittymd_template(tmp_path)

    assert "my-app" in result
    assert "jest" in result
    assert "JavaScript" in result
