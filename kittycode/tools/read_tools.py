"""
Read-only codebase introspection tools for KittyCode.

These tools give the agent the ability to *read* the project it is working on.
All paths are validated through the SandboxValidator before access.
"""

import os
import re
from pathlib import Path
from kittycode.tools.registry import ToolRegistry

# --- Constants ---
MAX_FILE_SIZE = 500 * 1024          # 500 KB
MAX_RETURN_CHARS = 8000             # Hard cap on returned text
MAX_GREP_MATCHES = 50               # Cap grep output
MAX_GREP_FILE_SIZE = 200 * 1024     # Skip files > 200 KB during grep
BINARY_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".zip", ".gz", ".tar", ".bz2", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".bin",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".pyc", ".pyo", ".class", ".o", ".obj",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".db", ".sqlite", ".sqlite3",
})


def _is_binary(filepath: Path) -> bool:
    """Quick heuristic: check extension, then sample first 1 KB for null bytes."""
    if filepath.suffix.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(1024)
        return b"\x00" in chunk
    except Exception:
        return True


# ─────────────────────────────────────────────────────────────────
# Tool 1: read_file
# ─────────────────────────────────────────────────────────────────

def action_read_file(path: str, start_line: int = 0, end_line: int = 0) -> str:
    """
    Read a file inside the sandbox and return its contents with line numbers.

    Args:
        path:       Absolute or sandbox-relative path to the file.
        start_line: First line to return (1-indexed). 0 = start of file.
        end_line:   Last line to return (1-indexed). 0 = end of file.

    Returns:
        The file contents prefixed with line numbers, or an error string.
    """
    try:
        target = Path(path)
        if not target.exists():
            return f"Error: File not found — {path}"
        if not target.is_file():
            return f"Error: Not a file — {path}"
        if target.stat().st_size > MAX_FILE_SIZE:
            size_kb = target.stat().st_size // 1024
            return f"Error: File too large ({size_kb} KB). Max is {MAX_FILE_SIZE // 1024} KB."
        if _is_binary(target):
            return f"Error: Binary file — cannot display {path}"

        with open(target, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)

        # Slice if range requested
        if start_line > 0 and end_line > 0:
            start_line = max(1, start_line)
            end_line = min(total_lines, end_line)
            selected = lines[start_line - 1 : end_line]
            offset = start_line
        else:
            selected = lines
            offset = 1

        # Format with line numbers
        width = len(str(offset + len(selected) - 1)) if selected else 1
        numbered = []
        for i, line in enumerate(selected):
            lineno = offset + i
            numbered.append(f"{lineno:>{width}} | {line.rstrip()}")

        output = "\n".join(numbered)

        # Truncate if too large
        if len(output) > MAX_RETURN_CHARS:
            truncated_lines = len(selected) - len(output[:MAX_RETURN_CHARS].split("\n"))
            output = output[:MAX_RETURN_CHARS] + f"\n[...{truncated_lines} lines truncated]"

        header = f"File: {path} ({total_lines} lines)"
        if start_line > 0 and end_line > 0:
            header += f"  [showing lines {start_line}-{end_line}]"
        return f"{header}\n{output}"

    except Exception as e:
        return f"Error reading file: {e}"


# ─────────────────────────────────────────────────────────────────
# Tool 2: grep
# ─────────────────────────────────────────────────────────────────

def action_grep(pattern: str, path: str = ".", recursive: bool = True) -> str:
    """
    Search for a regex pattern across files in the sandbox.

    Args:
        pattern:   A regex pattern to search for.
        path:      File or directory to search in (sandbox-relative or absolute).
        recursive: If path is a directory, search subdirectories too.

    Returns:
        Matching lines formatted as 'file.py:42: line content', or an info message.
    """
    try:
        compiled = re.compile(pattern)
    except re.error as e:
        return f"Error: Invalid regex pattern — {e}"

    target = Path(path)
    if not target.exists():
        return f"Error: Path not found — {path}"

    matches = []
    total_matches = 0

    def _search_file(filepath: Path):
        nonlocal total_matches
        if total_matches >= MAX_GREP_MATCHES:
            return

        if _is_binary(filepath):
            return
        try:
            if filepath.stat().st_size > MAX_GREP_FILE_SIZE:
                return
        except OSError:
            return

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                for lineno, line in enumerate(f, 1):
                    if compiled.search(line):
                        total_matches += 1
                        if len(matches) < MAX_GREP_MATCHES:
                            # Use relative path if possible for readability
                            try:
                                display_path = filepath.relative_to(Path.cwd())
                            except ValueError:
                                display_path = filepath
                            matches.append(
                                f"{display_path}:{lineno}: {line.rstrip()}"
                            )
                        if total_matches > MAX_GREP_MATCHES * 2:
                            return  # Stop scanning early if way over limit
        except Exception:
            pass  # Skip unreadable files silently

    if target.is_file():
        _search_file(target)
    elif target.is_dir():
        if recursive:
            for root, _dirs, files in os.walk(target):
                # Skip hidden dirs and common noise
                root_path = Path(root)
                if any(part.startswith(".") or part in ("node_modules", "__pycache__", ".git", "venv", ".venv")
                       for part in root_path.parts):
                    continue
                for fname in files:
                    _search_file(root_path / fname)
                    if total_matches >= MAX_GREP_MATCHES:
                        break
                if total_matches >= MAX_GREP_MATCHES:
                    break
        else:
            for item in target.iterdir():
                if item.is_file():
                    _search_file(item)
                    if total_matches >= MAX_GREP_MATCHES:
                        break
    else:
        return f"Error: '{path}' is not a file or directory."

    if not matches:
        return "No matches found."

    output = "\n".join(matches)
    if total_matches > MAX_GREP_MATCHES:
        overflow = total_matches - MAX_GREP_MATCHES
        output += f"\n[{overflow} more matches not shown]"

    return output


# ─────────────────────────────────────────────────────────────────
# Tool 3: find_symbol
# ─────────────────────────────────────────────────────────────────

def action_find_symbol(symbol: str, path: str = ".") -> str:
    """
    Find where a function, class, or variable is defined in the codebase.

    Args:
        symbol: The name of the function, class, or variable to locate.
        path:   Directory (or file) to search in.

    Returns:
        Matching definition lines with file + line number.
    """
    # Build patterns that match common Python/JS/TS definition sites
    patterns = [
        re.compile(rf"^\s*def\s+{re.escape(symbol)}\s*\("),          # Python function
        re.compile(rf"^\s*async\s+def\s+{re.escape(symbol)}\s*\("),   # Python async function
        re.compile(rf"^\s*class\s+{re.escape(symbol)}[\s:(]"),        # Python/JS class
        re.compile(rf"^\s*{re.escape(symbol)}\s*=\s*"),               # Variable assignment
        re.compile(rf"^\s*(const|let|var|export)\s+{re.escape(symbol)}\s*[=:]"),  # JS/TS variable
        re.compile(rf"^\s*(function|export\s+function)\s+{re.escape(symbol)}\s*\("),  # JS function
        re.compile(rf"^\s*{re.escape(symbol)}\s*:"),                  # YAML/dict key / type hint
    ]

    target = Path(path)
    if not target.exists():
        return f"Error: Path not found — {path}"

    results = []

    def _scan_file(filepath: Path):
        if _is_binary(filepath):
            return
        try:
            if filepath.stat().st_size > MAX_GREP_FILE_SIZE:
                return
        except OSError:
            return

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                for lineno, line in enumerate(f, 1):
                    for pat in patterns:
                        if pat.search(line):
                            try:
                                display_path = filepath.relative_to(Path.cwd())
                            except ValueError:
                                display_path = filepath
                            results.append(
                                f"{display_path}:{lineno}: {line.rstrip()}"
                            )
                            break  # One match per line is enough
                    if len(results) >= MAX_GREP_MATCHES:
                        return
        except Exception:
            pass

    if target.is_file():
        _scan_file(target)
    elif target.is_dir():
        for root, _dirs, files in os.walk(target):
            root_path = Path(root)
            if any(part.startswith(".") or part in ("node_modules", "__pycache__", ".git", "venv", ".venv")
                   for part in root_path.parts):
                continue
            for fname in files:
                _scan_file(root_path / fname)
                if len(results) >= MAX_GREP_MATCHES:
                    break
            if len(results) >= MAX_GREP_MATCHES:
                break

    if not results:
        return f"No definitions found for '{symbol}'."

    return "\n".join(results)


# ─────────────────────────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────────────────────────

def setup_read_tools(registry: ToolRegistry):
    """Register all read/search tools with the tool engine."""
    registry.register(
        name="read_file",
        description=(
            "Reads a file and returns its contents with line numbers. "
            "Optionally specify start_line and end_line (1-indexed) to read a range. "
            "Max file size: 500 KB. Returns at most 8000 characters."
        ),
        parameters={
            "path": "String. The file path to read (absolute or relative to project root).",
            "start_line": "Integer (optional). First line to return, 1-indexed. Default: 0 (start of file).",
            "end_line": "Integer (optional). Last line to return, 1-indexed. Default: 0 (end of file).",
        },
        func=action_read_file,
        destructive=False,
    )

    registry.register(
        name="grep",
        description=(
            "Searches for a regex pattern across files. Returns matching lines as "
            "'file.py:42: line content'. Max 50 matches. Skips binary files and files > 200 KB."
        ),
        parameters={
            "pattern": "String. A regex pattern to search for.",
            "path": "String (optional). File or directory to search. Default: '.' (project root).",
            "recursive": "Boolean (optional). Search subdirectories. Default: true.",
        },
        func=action_grep,
        destructive=False,
    )

    registry.register(
        name="find_symbol",
        description=(
            "Finds where a function, class, or variable is defined in the codebase. "
            "Searches for 'def symbol', 'class symbol', 'symbol =' patterns. "
            "Returns matching lines with file path and line number."
        ),
        parameters={
            "symbol": "String. The name of the function, class, or variable to find.",
            "path": "String (optional). Directory or file to search. Default: '.' (project root).",
        },
        func=action_find_symbol,
        destructive=False,
    )
