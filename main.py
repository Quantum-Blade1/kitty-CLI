"""Compatibility entrypoint for older installs.

Use `kittycode.cli.app:app` as the canonical console entrypoint.
"""

import sys
from pathlib import Path

# Ensure local package imports resolve when legacy launchers call this file directly.
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from kittycode.cli.app import app


if __name__ == "__main__":
    app()
