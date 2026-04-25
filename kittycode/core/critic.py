import logging
import re
from pathlib import Path
from typing import List, Dict
from kittycode.config.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)

# --- Safety Thresholds ---
MAX_WRITE_BYTES = 1024 * 1024       # 1 MB
MAX_MKDIR_DEPTH = 10                 # Max nested directory depth
DANGEROUS_EXTENSIONS = {".exe", ".bat", ".cmd", ".ps1", ".sh", ".vbs", ".dll", ".sys"}
SENSITIVE_PATTERNS = [
    re.compile(r"(^|[\\/])\.env$", re.IGNORECASE),
    re.compile(r"(^|[\\/])\.git[\\/]", re.IGNORECASE),
    re.compile(r"(^|[\\/])node_modules[\\/]", re.IGNORECASE),
    re.compile(r"(^|[\\/])__pycache__[\\/]", re.IGNORECASE),
]

class CriticVerdict:
    """Structured result from safety critic."""
    def __init__(self, allowed: bool, reason: str = "", tool_name: str = "", args: dict = None):
        self.allowed = allowed
        self.reason = reason
        self.tool_name = tool_name
        self.args = args or {}

    def __repr__(self):
        status = "ALLOW" if self.allowed else "BLOCK"
        return f"CriticVerdict({status}: {self.reason})"


class SafetyCritic:
    """
    Deterministic, rule-based pre-execution safety gate.
    Checks tool calls for dangerous paths, large writes, traversal,
    and unexpected parameters BEFORE the ToolEngine runs anything.
    """

    def __init__(self, project_root: Path = None):
        self.project_root = (project_root or PROJECT_ROOT).resolve()
        # Own sandbox instance — never touches the shared singleton
        from kittycode.security.sandbox import SandboxValidator
        self._sandbox = SandboxValidator(self.project_root)
        self._checks = {
            "write":  self._check_write,
            "mkdir":  self._check_mkdir,
            "ls":     self._check_ls,
            "run_cmd": self._check_run_cmd,
        }

    def review(self, tool_name: str, args: dict) -> CriticVerdict:
        """
        Reviews a single tool call. Returns CriticVerdict.
        Unknown tools get a generic parameter check.
        """
        # 1. Run tool-specific check if available
        checker = self._checks.get(tool_name)
        if checker:
            verdict = checker(args)
            if not verdict.allowed:
                return verdict

        # 2. Generic checks that apply to all tools with paths
        if "path" in args:
            verdict = self._check_path_safety(tool_name, args["path"])
            if not verdict.allowed:
                return verdict

        # 3. Check for unexpected/extra parameters
        verdict = self._check_unexpected_params(tool_name, args)
        if not verdict.allowed:
            return verdict

        return CriticVerdict(allowed=True, reason="Passed all safety checks", tool_name=tool_name, args=args)

    def review_batch(self, tool_calls: List[Dict]) -> List[CriticVerdict]:
        """Reviews a batch of tool calls. Returns list of verdicts."""
        return [
            self.review(tc.get("tool", ""), tc.get("args", {}))
            for tc in tool_calls
            if isinstance(tc, dict)
        ]

    # --- Path Safety ---

    def _check_path_safety(self, tool_name: str, path: str) -> CriticVerdict:
        """Check for traversal, symlinks, sensitive targets, and dangerous extensions."""
        from kittycode.security.sandbox import SandboxError

        # Containment + symlink check via critic's own sandbox instance
        try:
            resolved = self._sandbox.validate(path)
        except SandboxError as e:
            return CriticVerdict(False, str(e), tool_name, {"path": path})

        # Sensitive file/directory check
        path_str = str(resolved)
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(path_str):
                return CriticVerdict(False, f"Sensitive target blocked: '{path}' matches protected pattern", tool_name, {"path": path})

        # Dangerous extension check
        ext = Path(path).suffix.lower()
        if ext in DANGEROUS_EXTENSIONS:
            return CriticVerdict(False, f"Dangerous file type blocked: '{ext}' files cannot be created", tool_name, {"path": path})

        return CriticVerdict(True, "Path is safe", tool_name, {"path": path})

    # --- Tool-Specific Checks ---

    def _check_write(self, args: dict) -> CriticVerdict:
        """Check write operations for size limits and content safety."""
        content = args.get("content", "")
        path = args.get("path", "")

        # Size limit
        content_bytes = len(content.encode("utf-8", errors="replace"))
        if content_bytes > MAX_WRITE_BYTES:
            return CriticVerdict(
                False,
                f"Write too large: {content_bytes:,} bytes exceeds {MAX_WRITE_BYTES:,} byte limit",
                "write", args
            )

        # Check if content contains embedded tool calls (prompt injection vector)
        if re.search(r'\[\s*\{\s*"tool"\s*:', content):
            logger.warning(f"Potential prompt injection detected in write content for '{path}'")
            # Allow but log — content might legitimately contain JSON

        return CriticVerdict(True, "Write is safe", "write", args)

    def _check_mkdir(self, args: dict) -> CriticVerdict:
        """Check mkdir for excessive nesting depth."""
        path = args.get("path", "")
        depth = len(Path(path).parts)
        if depth > MAX_MKDIR_DEPTH:
            return CriticVerdict(
                False,
                f"Directory too deep: {depth} levels exceeds {MAX_MKDIR_DEPTH} limit",
                "mkdir", args
            )
        return CriticVerdict(True, "Mkdir is safe", "mkdir", args)

    def _check_ls(self, args: dict) -> CriticVerdict:
        """ls is always safe — just validate path exists."""
        return CriticVerdict(True, "Read-only operation", "ls", args)

    def _check_run_cmd(self, args: dict) -> CriticVerdict:
        command = str(args.get("command", "")).strip()
        if not command:
            return CriticVerdict(False, "run_cmd requires a non-empty command", "run_cmd", args)

        from kittycode.security.policy import validate_command

        allowed, reason = validate_command(command)
        if not allowed:
            return CriticVerdict(False, f"Command blocked by policy: {reason}", "run_cmd", args)
        return CriticVerdict(True, "Command accepted by policy", "run_cmd", args)

    # --- Generic Parameter Check ---

    def _check_unexpected_params(self, tool_name: str, args: dict) -> CriticVerdict:
        """Flag tool calls with suspiciously many or suspicious parameters."""
        KNOWN_PARAMS = {
            "write":   {"path", "content"},
            "mkdir":   {"path"},
            "ls":      {"path"},
            "run_cmd": {"command"},
            "mem":     {"key", "value"},
            "hello":   {"name"},
        }

        expected = KNOWN_PARAMS.get(tool_name)
        if expected is None:
            # Unknown tool (plugin) — allow but warn if >5 params
            if len(args) > 5:
                return CriticVerdict(False, f"Suspicious: {len(args)} parameters on unknown tool '{tool_name}'", tool_name, args)
            return CriticVerdict(True, "Plugin tool — params within limit", tool_name, args)

        unexpected = set(args.keys()) - expected
        if unexpected:
            return CriticVerdict(
                False,
                f"Unexpected parameters on '{tool_name}': {unexpected}",
                tool_name, args
            )

        return CriticVerdict(True, "Parameters valid", tool_name, args)
