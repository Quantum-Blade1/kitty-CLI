import importlib.util
import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


def detect_backend(root: Path) -> str:
    pyproject = root / "pyproject.toml"
    setup_py = root / "setup.py"

    if not pyproject.exists():
        return ""
    if importlib.util.find_spec("build") is not None:
        return "build"
    if setup_py.exists():
        return "setuptools"
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build KittyCode artifacts.")
    parser.add_argument("--check", action="store_true", help="Check build backend availability without building.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    backend = detect_backend(root)
    if not backend:
        print("No build backend available")
        return 1

    if args.check:
        print(f"build_backend={backend}")
        return 0

    if backend == "build":
        return run([sys.executable, "-m", "build"])

    if backend == "setuptools":
        print("build package not installed, falling back to setuptools build")
        return run([sys.executable, "setup.py", "sdist", "bdist_wheel"])

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
