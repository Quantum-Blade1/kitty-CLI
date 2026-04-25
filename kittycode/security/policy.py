import os
import shlex
import sys
from pathlib import PurePath
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
    "bash",
    "sh",
    "zsh",
    "fish",
    "cmd",
}

BLOCKED_ARG_PATTERNS = [
    "-enc",
    "--encodedcommand",
    "/c",
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
        use_posix = sys.platform != "win32"
        parts = shlex.split(cmd, posix=use_posix)
    except ValueError:
        return False, "Command parse failure"

    if not parts:
        return False, "No executable provided"

    # Strip surrounding quotes and normalize to bare executable name
    exe = parts[0].strip("\"'").lower()
    # Strip path prefix so "C:\Python\python.exe" -> "python"
    exe = PurePath(exe).stem

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
