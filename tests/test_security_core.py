"""Tests for KittyCode's security core: SandboxValidator and SafetyCritic."""

import os
import sys
import pytest
from pathlib import Path

from kittycode.security.sandbox import SandboxValidator, SandboxError


# =============================================================================
# SandboxValidator tests
# =============================================================================


def test_sandbox_allows_valid_path(tmp_path):
    """A path inside the sandbox root should resolve and be returned as absolute."""
    validator = SandboxValidator(root=tmp_path)
    result = validator.validate("subdir/file.txt")
    assert isinstance(result, Path)
    assert result.is_absolute()
    assert str(result).startswith(str(tmp_path))


def test_sandbox_blocks_traversal(tmp_path):
    """A ../ traversal outside the root must raise SandboxError."""
    validator = SandboxValidator(root=tmp_path)
    with pytest.raises(SandboxError):
        validator.validate("../escape")


def test_sandbox_blocks_absolute_path_outside(tmp_path):
    """An absolute path outside the sandbox root must be blocked."""
    validator = SandboxValidator(root=tmp_path)
    with pytest.raises(SandboxError):
        validator.validate("/etc/passwd")


def test_sandbox_singleton_not_rerooted(tmp_path):
    """Creating a separate SandboxValidator must NOT re-root the shared singleton."""
    from kittycode.security.sandbox import get_validator

    v1 = get_validator()
    # This creates a SEPARATE instance — should not touch the singleton
    _separate = SandboxValidator(tmp_path)
    v2 = get_validator()
    assert v1 is v2, "Singleton was re-rooted by a separate SandboxValidator instance"


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Symlink creation may require elevation on Windows",
)
def test_sandbox_symlink_escape(tmp_path):
    """A symlink pointing outside the sandbox must be blocked."""
    validator = SandboxValidator(root=tmp_path)
    link_path = tmp_path / "link"
    link_path.symlink_to(Path("/tmp"))
    with pytest.raises(SandboxError):
        validator.validate("link")


# =============================================================================
# SafetyCritic tests
# =============================================================================


def test_critic_blocks_traversal_path(tmp_path):
    """Critic must block write to a path that traverses outside the project root."""
    from kittycode.core.critic import SafetyCritic

    critic = SafetyCritic(project_root=tmp_path)
    verdict = critic.review("write", {"path": "../escape", "content": "x"})
    assert verdict.allowed is False


def test_critic_blocks_large_write(tmp_path):
    """Critic must block writes exceeding the 1 MB size limit."""
    from kittycode.core.critic import SafetyCritic

    critic = SafetyCritic(project_root=tmp_path)
    oversized = "x" * (1024 * 1024 + 1)
    verdict = critic.review("write", {"path": "file.txt", "content": oversized})
    assert verdict.allowed is False
    reason_lower = verdict.reason.lower()
    assert "large" in reason_lower or "exceed" in reason_lower


def test_critic_blocks_dangerous_extension(tmp_path):
    """Critic must block writes to dangerous file extensions (.exe, .bat, etc.)."""
    from kittycode.core.critic import SafetyCritic

    critic = SafetyCritic(project_root=tmp_path)
    verdict = critic.review("write", {"path": "evil.exe", "content": "x"})
    assert verdict.allowed is False


def test_critic_allows_safe_write(tmp_path):
    """Critic must allow a normal write to a safe path with reasonable content."""
    from kittycode.core.critic import SafetyCritic

    critic = SafetyCritic(project_root=tmp_path)
    verdict = critic.review("write", {"path": "src/main.py", "content": "print(1)"})
    assert verdict.allowed is True


def test_critic_blocks_shell_in_run_cmd(tmp_path):
    """Critic must block commands containing shell control operators."""
    from kittycode.core.critic import SafetyCritic

    critic = SafetyCritic(project_root=tmp_path)
    verdict = critic.review("run_cmd", {"command": "python && rm -rf /"})
    assert verdict.allowed is False


def test_critic_allows_python_c_flag(tmp_path):
    """python -c must be allowed after the Section 1 fix (removed -c from blocklist)."""
    from kittycode.core.critic import SafetyCritic

    critic = SafetyCritic(project_root=tmp_path)
    verdict = critic.review("run_cmd", {"command": 'python -c "print(1)"'})
    assert verdict.allowed is True
