"""
Codebase Indexer — Hierarchical repo scanning and metadata tagging.

This module builds a structured representation of the project to help
the agent understand the entry points, configuration, and layout without
hallucinating paths or structural roles.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ENTRY_POINT_NAMES = {"main.py", "__main__.py", "app.py", "index.py", "main.ts", "index.ts"}
CONFIG_FILE_NAMES = {"pyproject.toml", "package.json", "Cargo.toml", "go.mod", "setup.py", "requirements.txt"}
DOC_FILE_NAMES = {"README.md", "KITTY.md", "CHANGELOG.md", "CONTRIBUTING.md"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".kitty", "dist", "build", "venv", ".env"}
SKIP_EXTS = {".pyc", ".pyo", ".pyd", ".egg-info", ".so", ".dll", ".exe"}

class CodebaseIndex:
    def __init__(self, root: Path, max_files: int = 200):
        self.root = root
        self.max_files = max_files
        self._tree: list[dict] = []   # [{path, size, type, is_entry_point, is_config, is_doc}]
        self._ignore_patterns: list[str] = []
        self._load_gitignore()

    def _load_gitignore(self):
        """Loads simple line-by-line ignore patterns from .gitignore."""
        git_ignore = self.root / ".gitignore"
        if git_ignore.is_file():
            try:
                lines = git_ignore.read_text(encoding="utf-8").splitlines()
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Basic pattern normalization (remove trailing slashes)
                        self._ignore_patterns.append(line.rstrip("/"))
            except Exception:
                pass

    def _should_skip(self, name: str, is_dir: bool) -> bool:
        """Determines if a file or directory should be excluded from index."""
        if name in SKIP_DIRS:
            return True
        if not is_dir:
            if any(name.endswith(ext) for ext in SKIP_EXTS):
                return True
        
        # Simple .gitignore pattern matching (exact or prefix)
        for pattern in self._ignore_patterns:
            if name == pattern or name.startswith(pattern + os.sep):
                return True
        return False

    def build(self) -> "CodebaseIndex":
        """
        Scan the project directory tree using os.scandir for performance.
        Caps at self.max_files.
        """
        self._tree = []
        file_count = 0

        def _scan(current_root: Path):
            nonlocal file_count
            if file_count >= self.max_files:
                return

            try:
                with os.scandir(current_root) as it:
                    # Sort entries for consistent output (dirs first)
                    entries = sorted(it, key=lambda e: (not e.is_dir(), e.name.lower()))
                    for entry in entries:
                        if file_count >= self.max_files:
                            break

                        if self._should_skip(entry.name, entry.is_dir()):
                            continue

                        rel_path = os.path.relpath(entry.path, self.root)
                        
                        if entry.is_dir():
                            # Record directory but don't count towards file cap if it's just a folder
                            self._tree.append({
                                "path": rel_path,
                                "type": "dir",
                                "name": entry.name
                            })
                            _scan(Path(entry.path))
                        else:
                            # Record file
                            file_count += 1
                            meta = {
                                "path": rel_path,
                                "name": entry.name,
                                "type": "file",
                                "size": entry.stat().st_size if entry.stat().st_size < 1_000_000 else 1_000_001,
                                "is_entry": entry.name in ENTRY_POINT_NAMES,
                                "is_config": entry.name in CONFIG_FILE_NAMES,
                                "is_doc": entry.name in DOC_FILE_NAMES
                            }
                            if meta["size"] <= 1_000_000:
                                self._tree.append(meta)

            except PermissionError:
                pass

        _scan(self.root)
        if file_count >= self.max_files:
            logger.warning("Codebase index capped at %d files. Some files were not indexed.", self.max_files)
        return self

    def to_prompt_block(self, max_chars: int = 3000) -> str:
        """
        Returns a hierarchical text tree block for system prompt injection.
        """
        if not self._tree:
            return "[Codebase Index: Empty or not built]"

        lines = [f"PROJECT FILE TREE ({len([t for t in self._tree if t['type']=='file'])} files indexed)"]
        
        # Build a nested structure for easier rendering
        for item in self._tree:
            rel_path = item["path"]
            depth = rel_path.count(os.sep)
            indent = "  " * depth
            
            label = item["name"]
            if item["type"] == "dir":
                line = f"{indent}{label}/"
            else:
                tags = []
                if item.get("is_entry"): tags.append("ENTRY")
                if item.get("is_config"): tags.append("CONFIG")
                if item.get("is_doc"): tags.append("DOC")
                
                tag_str = f"  [{', '.join(tags)}]" if tags else ""
                line = f"{indent}{label}{tag_str}"
            
            if sum(len(l) + 1 for l in lines) + len(line) > max_chars:
                lines.append(f"{indent}... ({len(self._tree) - self._tree.index(item)} more items truncated)")
                break
            lines.append(line)

        return "\n".join(lines)

    def get_entry_points(self) -> list[str]:
        """Return relative paths of all marked entry point files."""
        return [t["path"] for t in self._tree if t.get("is_entry")]

    def get_key_file_content(self, path: str) -> str:
        """Return first 200 chars of a key file (config/README)."""
        # Verify path is in index and is a key file
        found = next((t for t in self._tree if t["path"] == path), None)
        if not found or found["type"] != "file":
            return ""
        
        if not (found.get("is_config") or found.get("is_doc")):
            return ""

        full_path = self.root / path
        if full_path.is_file():
            try:
                return full_path.read_text(encoding="utf-8")[:200]
            except Exception:
                pass
        return ""
