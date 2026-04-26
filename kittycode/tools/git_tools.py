import subprocess
import os
from kittycode.tools.registry import ToolRegistry
from kittycode.config.settings import PROJECT_ROOT

def _run_git(args: list[str]) -> str:
    try:
        process = subprocess.Popen(
            ["git"] + args,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        stdout, _ = process.communicate()
        return stdout.strip() or f"Git command '{' '.join(args)}' finished with code {process.returncode}"
    except Exception as e:
        return f"Git error: {str(e)}"

def action_git_status() -> str:
    """Returns the current git status."""
    return _run_git(["status", "--short"])

def action_git_diff() -> str:
    """Returns the current git diff of staged and unstaged changes."""
    return _run_git(["diff", "HEAD"])

def action_git_commit(message: str) -> str:
    """Stages all changes and commits them."""
    # First stage everything
    _run_git(["add", "."])
    # Then commit
    return _run_git(["commit", "-m", message])

def setup_git_tools(registry: ToolRegistry):
    registry.register(
        name="git_status",
        description="Shows the status of the git repository (staged/unstaged changes).",
        parameters={},
        func=action_git_status,
        destructive=False
    )
    
    registry.register(
        name="git_diff",
        description="Shows the diff of modified files in the repository.",
        parameters={},
        func=action_git_diff,
        destructive=False
    )
    
    registry.register(
        name="git_commit",
        description="Stages all changes and commits them with a message.",
        parameters={"message": "String. The commit message."},
        func=action_git_commit,
        destructive=True
    )
