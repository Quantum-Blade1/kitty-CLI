import os
import sys
import subprocess
import shlex
from kittycode.tools.registry import ToolRegistry

SUBPROCESS_TIMEOUT_S = 60

# --- Action Engine Protocol (JSON Format) ---

def action_mkdir(path: str) -> str:
    try:
        os.makedirs(path, exist_ok=True)
        return f"Folder Created: {path}"
    except Exception as e:
        return f"Failed to create folder: {str(e)}"

def action_write_raw(path: str, content: str = "") -> str:
    """Internal raw write without diffs or prompts."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"File Written: {path}"
    except Exception as e:
        return f"Failed to write file: {str(e)}"

def action_write(path: str, content: str = "", diff_mode: bool = True) -> str:
    """Writes content to a file with unified diff preview and confirmation."""
    from pathlib import Path
    from rich.prompt import Confirm
    from kittycode.cli.ui import console
    from kittycode.utils.diff_utils import unified_diff, render_diff_rich

    p = Path(path)
    
    if diff_mode and p.exists():
        try:
            old_content = p.read_text(encoding="utf-8", errors="replace")
            if old_content == content:
                return f"No changes: {path} is already up to date."
            
            diff = unified_diff(old_content, content, path)
            console.print(f"\n[bold yellow]Proposed Changes: {path}[/bold yellow]")
            render_diff_rich(diff)
            
            # Stop the Rich spinner if it's active in the console's state
            # (In our app, we usually pass 'status' object to ToolEngine, but here we prompt directly)
            # Typer/Rich prompts handle terminal suspension well.
            confirmed = Confirm.ask(f"Apply these changes to {path}?", default=False)
            if not confirmed:
                return f"Write cancelled by user: {path}"
        except Exception as e:
            console.print(f"[red]Error during diff: {e}[/red]")
            # Fallback to simple confirmation if diff fails
            if not Confirm.ask(f"Diff failed. Overwrite {path} anyway?", default=False):
                return f"Write cancelled by user: {path}"

    elif diff_mode and not p.exists():
        preview = "\n".join(content.splitlines()[:5])
        console.print(f"\n[teal]New file: {path}[/teal]")
        console.print(preview + ("\n..." if len(content.splitlines()) > 5 else ""))
        confirmed = Confirm.ask(f"Create {path}?", default=False)
        if not confirmed:
            return f"Write cancelled by user: {path}"

    return action_write_raw(path, content)


def action_ls(path: str) -> str:
    try:
        if not os.path.exists(path):
            return f"Error: {path} not found"
        items = os.listdir(path)
        return f"Contents of {path}: " + (", ".join(items) if items else "Empty")
    except Exception as e:
        return f"Failed to list directory: {str(e)}"

def action_ls_tree(path: str = ".", max_depth: int = 3) -> str:
    """Returns a visual tree of the directory structure."""
    try:
        from rich.tree import Tree
        from rich.console import Console
        from io import StringIO
        
        root_path = os.path.abspath(path)
        if not os.path.exists(root_path):
            return f"Error: {path} not found"
            
        tree = Tree(f"[bold blue]{os.path.basename(root_path)}/[/bold blue]")
        
        def _build_tree(current_path: str, current_tree: Tree, depth: int):
            if depth > max_depth:
                return
            
            try:
                # Sort: directories first, then files
                items = sorted(os.listdir(current_path), key=lambda x: (not os.path.isdir(os.path.join(current_path, x)), x.lower()))
            except Exception:
                return
                
            for item in items:
                if item.startswith(".") or item == "__pycache__" or item == "node_modules":
                    continue
                    
                full_path = os.path.join(current_path, item)
                if os.path.isdir(full_path):
                    node = current_tree.add(f"[bold blue]{item}/[/bold blue]")
                    _build_tree(full_path, node, depth + 1)
                else:
                    current_tree.add(item)
                    
        _build_tree(root_path, tree, 1)
        
        # Capture Rich output
        output_console = Console(file=StringIO(), force_terminal=True, width=80)
        output_console.print(tree)
        return output_console.file.getvalue()
    except Exception as e:
        return f"Failed to generate tree: {str(e)}"

def action_run_cmd(command: str) -> str:
    try:
        from kittycode.cli.ui import console

        # Policy already enforced by SafetyCritic before this runs.

        # Stop any active spinner UI so the raw stdout can be seen cleanly
        active_status = hasattr(console, "_status") and console._status
        if active_status:
            active_status.stop()

        console.print(f"\n[kmuted]— Spawning Process: {command} —[/kmuted]")

        process = subprocess.Popen(
            shlex.split(command, posix=(sys.platform != "win32")),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            stdout, _ = process.communicate(timeout=SUBPROCESS_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, _ = process.communicate()
            stdout = (stdout or "") + f"\n[TIMEOUT] Killed after {SUBPROCESS_TIMEOUT_S}s"

        # Resume the spinner
        console.print(f"[kmuted]— Execution finished (Code: {process.returncode}) —[/kmuted]\n")
        if active_status:
            active_status.start()

        output = (stdout or "").strip()
        # Truncate output payload so we don't blow up the LLM context window with npm logs
        if len(output) > 2000:
            output = output[:1000] + "\n...[Output Truncated]...\n" + output[-1000:]

        return f"Command Executed: {command}\nOutput:\n{output}" if output else f"Command Executed: {command} (No output)"

    except Exception as e:
        return f"Failed to run command: {str(e)}"

def setup_fs_tools(registry: ToolRegistry):
    registry.register(
        name="mkdir",
        description="Creates a new directory at the specified path.",
        parameters={"path": "String. The path to the new directory."},
        func=action_mkdir,
        destructive=True # Requires confirmation
    )

    registry.register(
        name="write",
        description="Writes content to a file at the specified path.",
        parameters={"path": "String. The file path.", "content": "String. The content to write."},
        func=action_write,
        destructive=True # Requires confirmation
    )

    registry.register(
        name="write_raw",
        description="Writes content to a file without showing diffs or prompting for confirmation. Use ONLY for automated multi-step operations.",
        parameters={"path": "String. The file path.", "content": "String. The content to write."},
        func=action_write_raw,
        destructive=True
    )

    registry.register(
        name="ls",
        description="Lists the contents of a directory.",
        parameters={"path": "String. The directory path to list."},
        func=action_ls,
        destructive=False
    )



    registry.register(
        name="ls_tree",
        description="Displays a visual tree of the codebase structure.",
        parameters={"path": "String (optional). The root path. Default: '.'", "max_depth": "Integer (optional). Max depth to recurse. Default: 3."},
        func=action_ls_tree,
        destructive=False
    )

    registry.register(
        name="run_cmd",
        description="Runs a shell command on the user's terminal.",
        parameters={"command": "String. The exact shell command to run."},
        func=action_run_cmd,
        destructive=True # Requires confirmation
    )
