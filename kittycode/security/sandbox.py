"""
Centralized sandbox path validator for KittyCode.

WHY THIS IS SAFE:
1. resolve() canonicalizes the path — removes .., ., normalizes separators
2. os.path.commonpath() compares real filesystem paths — case-insensitive on
   Windows automatically (ntpath vs posixpath), no string hacks needed
3. Symlinks are explicitly resolved THEN checked — a symlink pointing outside
   the sandbox will resolve to its real target, which will fail containment
4. is_symlink() check on the pre-resolved path catches symlinks that point
   outside the project, even if the symlink itself is inside it

This module is the SINGLE SOURCE OF TRUTH for path validation.
ToolEngine and SafetyCritic both delegate here.
"""

import logging
import os
from pathlib import Path
from kittycode.config.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)


class SandboxError(PermissionError):
    """Raised when a path violates sandbox constraints."""
    pass


class SandboxValidator:
    """
    Cross-platform path containment validator.
    All file operations MUST pass through validate() before execution.
    """

    def __init__(self, root: Path = None):
        # Resolve once at init — this is the canonical sandbox boundary
        self._root = (root or PROJECT_ROOT).resolve()

    @property
    def root(self) -> Path:
        return self._root

    def validate(self, target_path: str) -> Path:
        """
        Validates and resolves a target path within the sandbox.

        Returns the resolved absolute Path if safe.
        Raises SandboxError if unsafe.

        Checks performed (in order):
        1. Path resolution (canonicalize all .., ., and separators)
        2. Containment via os.path.commonpath (cross-platform, case-aware)
        3. Symlink target verification (reject symlinks pointing outside)
        """
        try:
            # Step 1: Resolve to absolute canonical path
            candidate = (self._root / target_path).resolve()
        except (ValueError, OSError) as e:
            raise SandboxError(f"Invalid path '{target_path}': {e}")

        # Step 2: Containment check using os.path.commonpath
        # This is case-insensitive on Windows automatically (uses ntpath)
        # and case-sensitive on Linux/macOS (uses posixpath) — correct behavior
        try:
            common = Path(os.path.commonpath([str(self._root), str(candidate)]))
            if common != self._root:
                raise SandboxError(
                    f"Path traversal blocked: '{target_path}' resolves outside sandbox "
                    f"(common ancestor: {common}, expected: {self._root})"
                )
        except ValueError:
            # os.path.commonpath raises ValueError if paths are on different drives (Windows)
            raise SandboxError(
                f"Path '{target_path}' is on a different drive than the sandbox root"
            )

        # Step 3: Symlink check — the raw (un-resolved) path might be a symlink
        # If it exists and is a symlink, verify its target is also inside sandbox
        raw_path = self._root / target_path
        if raw_path.exists() and raw_path.is_symlink():
            real_target = raw_path.resolve()
            try:
                common = Path(os.path.commonpath([str(self._root), str(real_target)]))
                if common != self._root:
                    raise SandboxError(
                        f"Symlink escape blocked: '{target_path}' links to '{real_target}' "
                        f"which is outside the sandbox"
                    )
            except ValueError:
                raise SandboxError(
                    f"Symlink '{target_path}' points to a different drive"
                )

        return candidate

    def resolve_safe(self, target_path: str) -> str:
        """
        Convenience wrapper — returns validated path as string.
        Drop-in replacement for ToolEngine._resolve_safe_path().
        """
        return str(self.validate(target_path))


# Module-level singleton for shared use
_default_validator = None

def get_validator(root: Path = None) -> SandboxValidator:
    """Returns the shared SandboxValidator singleton."""
    global _default_validator
    if _default_validator is None or root is not None:
        _default_validator = SandboxValidator(root)
    return _default_validator
