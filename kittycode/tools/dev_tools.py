"""
Dev Tools — Test running and failure parsing.
"""

import os
import subprocess
import re
from kittycode.tools.registry import ToolRegistry
from kittycode.config.settings import PROJECT_ROOT


def action_run_tests(test_cmd: str = "", path: str = ".") -> dict:
    """
    Run the project test suite and return structured results.
    """
    if not test_cmd:
        # Auto-detect
        if (PROJECT_ROOT / "pytest.ini").exists() or (PROJECT_ROOT / "pyproject.toml").exists():
            test_cmd = "pytest"
        elif (PROJECT_ROOT / "package.json").exists():
            test_cmd = "npm test"
        elif (PROJECT_ROOT / "Cargo.toml").exists():
            test_cmd = "cargo test"
        elif (PROJECT_ROOT / "go.mod").exists():
            test_cmd = "go test ./..."
        else:
            test_cmd = "pytest" # Default fallback

    try:
        process = subprocess.Popen(
            test_cmd,
            shell=True,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        stdout, _ = process.communicate(timeout=120)
        
        passed = (process.returncode == 0)
        output = stdout[-4000:] if len(stdout) > 4000 else stdout
        
        # Simple failure parsing for pytest
        failures = []
        # Look for FAILED path/to/test.py::test_name - AssertionError: ...
        # and also the more detailed failure blocks
        failed_lines = re.findall(r"FAILED\s+(.*?)::(.*?)\s+-\s+(.*)", stdout)
        for f in failed_lines:
            failures.append({
                "file": f[0],
                "test": f[1],
                "error": f[2].strip()
            })
            
        # Summary extraction (e.g. "3 failed, 12 passed in 1.2s")
        summary_match = re.search(r"==.* ([\d]+ failed|[\d]+ passed|[\d]+ error).* in [\d.]+s ==", stdout)
        summary = summary_match.group(1) if summary_match else "Test run finished."

        return {
            "passed": passed,
            "exit_code": process.returncode,
            "output": output,
            "failures": failures,
            "summary": summary,
            "command": test_cmd
        }
    except subprocess.TimeoutExpired:
        return {"passed": False, "error": "Tests timed out after 120s", "output": ""}
    except Exception as e:
        return {"passed": False, "error": str(e), "output": ""}


def setup_dev_tools(registry: ToolRegistry):
    registry.register(
        name="run_tests",
        description="Runs the project test suite and returns structured results (failures, summary).",
        parameters={"test_cmd": "String (optional). Custom test command.", "path": "String (optional). Root directory."},
        func=action_run_tests,
        destructive=False
    )
