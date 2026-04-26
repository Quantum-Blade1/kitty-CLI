import difflib
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text
from io import StringIO

def generate_unified_diff(path: str, old_content: str, new_content: str) -> str:
    """
    Generates a colorized unified diff for display in the terminal.
    """
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines, 
        new_lines, 
        fromfile=f"a/{path}", 
        tofile=f"b/{path}",
        lineterm=""
    )
    
    diff_text = "".join(diff)
    if not diff_text:
        return "[no changes]"
        
    return diff_text

def render_diff_panel(path: str, diff_text: str) -> Panel:
    """
    Renders the diff in a beautiful Rich panel.
    """
    # Simple colorization for the diff
    lines = diff_text.splitlines()
    styled_text = Text()
    
    for line in lines:
        if line.startswith("+++") or line.startswith("---"):
            styled_text.append(line + "\n", style="bold white")
        elif line.startswith("@@"):
            styled_text.append(line + "\n", style="cyan")
        elif line.startswith("+"):
            styled_text.append(line + "\n", style="green")
        elif line.startswith("-"):
            styled_text.append(line + "\n", style="red")
        else:
            styled_text.append(line + "\n")
            
    return Panel(
        styled_text,
        title=f"[bold]Proposed Changes: {path}[/bold]",
        subtitle="Review changes carefully",
        border_style="yellow",
        padding=(1, 2)
    )
