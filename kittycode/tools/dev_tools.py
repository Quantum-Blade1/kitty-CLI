"""
Dev Tools — Test running, failure parsing, and Git operations.
"""

import os
import subprocess
import re
from rich.prompt import Confirm
from kittycode.tools.registry import ToolRegistry
from kittycode.config.settings import PROJECT_ROOT


# ─────────────────────────────────────────────────────────────────
# Test Tools
# ─────────────────────────────────────────────────────────────────

def action_run_tests(test_cmd: str = "", path: str = ".") -> dict:
    """
    Run the project test suite and return structured results.
    """
    if not test_cmd:
        # Auto-detect
        if (PROJECT_ROOT / "pytest.ini").exists() or (PROJECT_ROOT / "pyproject.toml").exists():
            test_cmd = "pytest"
        elif (PROJECT_ROOT / "package.json").exists():
            test_cmd = "npm test"
        elif (PROJECT_ROOT / "Cargo.toml").exists():
            test_cmd = "cargo test"
        elif (PROJECT_ROOT / "go.mod").exists():
            test_cmd = "go test ./..."
        else:
            test_cmd = "pytest" # Default fallback

    try:
        process = subprocess.Popen(
            test_cmd,
            shell=True,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        stdout, _ = process.communicate(timeout=120)
        
        passed = (process.returncode == 0)
        output = stdout[-4000:] if len(stdout) > 4000 else stdout
        
        # Simple failure parsing for pytest
        failures = []
        failed_lines = re.findall(r"FAILED\s+(.*?)::(.*?)\s+-\s+(.*)", stdout)
        for f in failed_lines:
            failures.append({
                "file": f[0],
                "test": f[1],
                "error": f[2].strip()
            })
            
        summary_match = re.search(r"==.* ([\d]+ failed|[\d]+ passed|[\d]+ error).* in [\d.]+s ==", stdout)
        summary = summary_match.group(1) if summary_match else "Test run finished."

        return {
            "passed": passed,
            "exit_code": process.returncode,
            "output": output,
            "failures": failures,
            "summary": summary,
            "command": test_cmd
        }
    except subprocess.TimeoutExpired:
        return {"passed": False, "error": "Tests timed out after 120s", "output": ""}
    except Exception as e:
        return {"passed": False, "error": str(e), "output": ""}


# ─────────────────────────────────────────────────────────────────
# Git Tools
# ─────────────────────────────────────────────────────────────────

def _run_git(args: list[str]) -> str:
    """Internal helper to run git commands safely."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=False,
            timeout=30
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Git error: {e.output.strip()}"
    except FileNotFoundError:
        return "Git error: git command not found. Is git installed?"
    except subprocess.TimeoutExpired:
        return "Git error: command timed out after 30s"
    except Exception as e:
        return f"Git error: {str(e)}"


def action_git_status() -> str:
    """Returns current git status --short."""
    out = _run_git(["status", "--short"])
    if not out:
        return "Working tree clean."
    return out


def action_git_diff(path: str = "") -> str:
    """Returns the git diff for a specific path or the whole repo."""
    args = ["diff"]
    if path:
        args.extend(["--", path])
    
    out = _run_git(args)
    if not out:
        return "No changes."
    
    if len(out) > 5000:
        return out[:5000] + "\n\n[...diff truncated — too large for context]"
    return out


def action_git_commit(message: str) -> str:
    """Stages all changes and commits them after user confirmation."""
    from kittycode.cli.ui import console
    
    # 1. Stage all
    add_out = _run_git(["add", "-A"])
    if "Git error" in add_out:
        return add_out

    # 2. Confirm
    status_out = action_git_status()
    console.print(f"\n[bold yellow]Preparing to commit changes:[/bold yellow]\n{status_out}")
    if not Confirm.ask(f"Commit with message: '{message}'?", default=False):
        return "Commit cancelled by user."

    # 3. Commit
    commit_out = _run_git(["commit", "-m", message])
    if "Git error" in commit_out:
        return commit_out
    
    # Parse hash (first 7 chars usually appear in output like "[main 0a82122] ...")
    m = re.search(r"\[.*? (.*?)\]", commit_out)
    hash_str = m.group(1) if m else "unknown"
    return f"Commit successful. Hash: {hash_str}"


def action_git_branch(name: str) -> str:
    """Creates a new branch or switches to an existing one."""
    from kittycode.cli.ui import console
    
    # Check if branch exists
    branches = _run_git(["branch"])
    exists = any(b.strip().strip("* ").strip() == name for b in branches.splitlines())
    
    if exists:
        if not Confirm.ask(f"Switch to existing branch '{name}'?", default=True):
            return "Branch switch cancelled."
        return _run_git(["checkout", name])
    else:
        if not Confirm.ask(f"Create and switch to new branch '{name}'?", default=True):
            return "Branch creation cancelled."
        return _run_git(["checkout", "-b", name])


def action_git_log(n: int = 5) -> str:
    """Returns the last N commit messages."""
    return _run_git(["log", "--oneline", f"-{n}"])


def setup_dev_tools(registry: ToolRegistry):
    # Tests
    registry.register(
        name="run_tests",
        description="Runs the project test suite and returns structured results (failures, summary).",
        parameters={"test_cmd": "String (optional). Custom test command.", "path": "String (optional). Root directory."},
        func=action_run_tests,
        destructive=False
    )
    
    # Git
    registry.register(
        name="git_status",
        description="Shows the short status of the git repository.",
        parameters={},
        func=action_git_status,
        destructive=False
    )
    registry.register(
        name="git_diff",
        description="Shows the diff of unstaged changes. Use before writing to check existing modifications.",
        parameters={"path": "String (optional). Specific file/folder to diff."},
        func=action_git_diff,
        destructive=False
    )
    registry.register(
        name="git_commit",
        description="Stages all changes and commits them with a message. Requires user confirmation.",
        parameters={"message": "String. The commit message."},
        func=action_git_commit,
        destructive=True
    )
    registry.register(
        name="git_branch",
        description="Creates or switches to a git branch. Requires user confirmation.",
        parameters={"name": "String. The branch name."},
        func=action_git_branch,
        destructive=True
    )
    registry.register(
        name="git_log",
        description="Shows the last N commit messages.",
        parameters={"n": "Integer (optional). Number of commits to show. Default 5."},
        func=action_git_log,
        destructive=False
    )
