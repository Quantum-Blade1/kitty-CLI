import os
import shlex
from typing import List, Tuple


DEFAULT_ALLOWED_PREFIXES = [
    "python",
    "pytest",
    "pip",
    "git",
    "npm",
    "node",
    "uv",
    "cargo",
    "go",
    "dotnet",
    "ls",
    "dir",
    "type",
    "cat",
    "echo",
]

BLOCKED_TOKENS = [
    "&&",
    "||",
    ";",
    "|",
    ">",
    "<",
    "`",
    "$(",
]

BLOCKED_EXECUTABLES = {
    "rm",
    "rmdir",
    "del",
    "format",
    "shutdown",
    "reboot",
    "mkfs",
    "diskpart",
    "reg",
    "powershell",
    "pwsh",
}

BLOCKED_ARG_PATTERNS = [
    "-enc",
    "--encodedcommand",
    "/c",
    "-c",
]


def _allowed_prefixes() -> List[str]:
    raw = os.getenv("KITTY_CMD_ALLOWLIST", "").strip()
    if not raw:
        return DEFAULT_ALLOWED_PREFIXES
    return [x.strip().lower() for x in raw.split(",") if x.strip()]


def validate_command(command: str) -> Tuple[bool, str]:
    """
    Validate run_cmd command policy.
    Returns (allowed, reason).
    """
    cmd = command.strip()
    if not cmd:
        return False, "Empty command"

    for token in BLOCKED_TOKENS:
        if token in cmd:
            return False, f"Blocked shell control token: {token}"

    try:
        parts = shlex.split(cmd, posix=False)
    except ValueError:
        return False, "Command parse failure"

    if not parts:
        return False, "No executable provided"

    exe = parts[0].lower()
    allowed = _allowed_prefixes()

    if exe in BLOCKED_EXECUTABLES:
        return False, f"Blocked executable: {exe}"

    if exe not in allowed:
        return False, f"Executable '{exe}' not in allowlist"

    lowered_args = [p.lower() for p in parts[1:]]
    for arg in lowered_args:
        for bad in BLOCKED_ARG_PATTERNS:
            if arg == bad:
                return False, f"Blocked argument pattern: {bad}"

    return True, "Allowed by policy"
