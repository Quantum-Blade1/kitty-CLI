import os
import sys
import subprocess
import shlex
from kittycode.tools.registry import ToolRegistry

# --- Action Engine Protocol (JSON Format) ---

def action_mkdir(path: str) -> str:
    try:
        os.makedirs(path, exist_ok=True)
        return f"Folder Created: {path}"
    except Exception as e:
        return f"Failed to create folder: {str(e)}"

def action_write(path: str, content: str = "") -> str:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"File Written: {path}"
    except Exception as e:
        return f"Failed to write file: {str(e)}"

def action_ls(path: str) -> str:
    try:
        if not os.path.exists(path):
            return f"Error: {path} not found"
        items = os.listdir(path)
        return f"Contents of {path}: " + (", ".join(items) if items else "Empty")
    except Exception as e:
        return f"Failed to list directory: {str(e)}"

def action_run_cmd(command: str) -> str:
    try:
        from kittycode.cli.ui import console
        from kittycode.security.policy import validate_command

        allowed, reason = validate_command(command)
        if not allowed:
            return f"Blocked by command policy: {reason}"

        # Stop any active spinner UI so the raw stdout can be seen cleanly
        active_status = hasattr(console, "_status") and console._status
        if active_status:
            active_status.stop()
            
        console.print(f"\n[kmuted]— Spawning Process: {command} —[/kmuted]")
        
        # Run command iteratively, streaming stdout and stderr to the console live
        process = subprocess.Popen(
            shlex.split(command, posix=False),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout stream
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        output_lines = []
        for line in process.stdout:
            sys.stdout.write(line) # Pipe raw to terminal
            sys.stdout.flush()
            output_lines.append(line)
            
        process.wait()
        
        # Resume the spinner
        console.print(f"[kmuted]— Execution finished (Code: {process.returncode}) —[/kmuted]\n")
        if active_status:
            active_status.start()
            
        output = "".join(output_lines).strip()
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
        name="ls",
        description="Lists the contents of a directory.",
        parameters={"path": "String. The directory path to list."},
        func=action_ls,
        destructive=False
    )
    
    registry.register(
        name="run_cmd",
        description="Runs a shell command on the user's terminal.",
        parameters={"command": "String. The exact shell command to run."},
        func=action_run_cmd,
        destructive=True # Requires confirmation
    )
