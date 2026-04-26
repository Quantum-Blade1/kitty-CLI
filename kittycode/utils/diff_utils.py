"""
Diff Utilities — Unified diff generation and Rich-based rendering.
"""

import difflib
from kittycode.cli.ui import console


def unified_diff(old_content: str, new_content: str, filename: str) -> str:
    """
    Returns a unified diff string (like `diff -u`).
    Uses difflib.unified_diff().
    Returns empty string if old_content == new_content (no changes).
    """
    if old_content == new_content:
        return ""

    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()
    
    diff = difflib.unified_diff(
        old_lines, 
        new_lines, 
        fromfile=f"a/{filename}", 
        tofile=f"b/{filename}",
        lineterm=""
    )
    
    return "\n".join(diff)


def render_diff_rich(diff: str) -> None:
    """
    Prints the diff to the terminal with Rich colours.
    """
    if not diff:
        return

    from rich.text import Text
    styled_text = Text()
    
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            styled_text.append(line + "\n", style="green")
        elif line.startswith("-") and not line.startswith("---"):
            styled_text.append(line + "\n", style="red")
        elif line.startswith("@@"):
            styled_text.append(line + "\n", style="cyan")
        elif line.startswith("---") or line.startswith("+++"):
            styled_text.append(line + "\n", style="bold white")
        else:
            styled_text.append(line + "\n", style="dim white")
            
    console.print(styled_text)
