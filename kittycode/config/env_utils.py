import os
from pathlib import Path
from kittycode.config.settings import ENV_PATH

def save_env_var(key: str, value: str):
    """Saves or updates an environment variable in the global .env file."""
    lines = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text().splitlines()
    
    found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}=") or line.startswith(f"export {key}="):
            new_lines.append(f'{key}="{value}"')
            found = True
        else:
            new_lines.append(line)
    
    if not found:
        new_lines.append(f'{key}="{value}"')
    
    ENV_PATH.write_text("\n".join(new_lines) + "\n")
