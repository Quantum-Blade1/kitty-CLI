import subprocess
import os
import re
from kittycode.tools.registry import ToolRegistry
from kittycode.config.settings import PROJECT_ROOT
from kittycode.context.kittymd import load_kittymd

def action_run_tests(command: str = "") -> str:
    """
    Runs the project test suite. 
    If command is not provided, it attempts to extract it from KITTY.md.
    """
    if not command:
        # Try to extract from KITTY.md
        kittymd = load_kittymd(PROJECT_ROOT)
        if kittymd:
            # Look for a block like "Run all tests\npytest"
            match = re.search(r"Run all tests\s*\n\s*([^\n]+)", kittymd, re.IGNORECASE)
            if match:
                command = match.group(1).strip()
    
    if not command:
        # Fallback detection
        if (PROJECT_ROOT / "pytest.ini").exists() or (PROJECT_ROOT / "tests").exists():
            command = "pytest"
        elif (PROJECT_ROOT / "package.json").exists():
            command = "npm test"
        else:
            return "Error: No test command found in KITTY.md and auto-detection failed. Please provide a command."

    try:
        from kittycode.cli.ui import console
        console.print(f"\n[kmuted]— Running Tests: {command} —[/kmuted]")
        
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        stdout, _ = process.communicate()
        
        output = stdout.strip()
        # Truncate output
        if len(output) > 3000:
            output = output[:1500] + "\n...[Output Truncated]...\n" + output[-1500:]
            
        status = "PASSED" if process.returncode == 0 else "FAILED"
        return f"Tests {status} (Command: {command})\nOutput:\n{output}"
    except Exception as e:
        return f"Test Execution Error: {str(e)}"

def setup_test_tools(registry: ToolRegistry):
    registry.register(
        name="run_tests",
        description="Runs the project test suite. Auto-detects the command from KITTY.md or common defaults.",
        parameters={"command": "String (optional). Specific test command to run."},
        func=action_run_tests,
        destructive=False
    )
