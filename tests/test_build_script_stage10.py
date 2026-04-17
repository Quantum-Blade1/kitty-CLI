import subprocess
import sys
from pathlib import Path


def test_build_script_exists():
    assert Path("scripts/build_artifacts.py").exists()


def test_build_script_runs():
    proc = subprocess.run(
        [sys.executable, "scripts/build_artifacts.py", "--check"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "build_backend=" in proc.stdout
