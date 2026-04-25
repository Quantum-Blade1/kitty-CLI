import os
from pathlib import Path
from dotenv import load_dotenv

# --- Configuration & Persistence ---
# Global configs
KITTY_GLOBAL_DIR = Path.home() / ".kittycode"
KITTY_GLOBAL_DIR.mkdir(exist_ok=True)
ENV_PATH = KITTY_GLOBAL_DIR / ".env"

# Project-scoped configs
def get_project_root() -> Path:
    """Returns the current working directory as the project root."""
    return Path.cwd()

# Backward-compat module-level variable (resolved at import)
PROJECT_ROOT = get_project_root()
KITTY_PROJECT_DIR = PROJECT_ROOT / ".kitty"
KITTY_PROJECT_DIR.mkdir(exist_ok=True)

MEMORY_FILE = KITTY_PROJECT_DIR / "memory.json"
HEALTH_FILE = KITTY_PROJECT_DIR / "model_health.json"
STRATEGY_FILE = KITTY_PROJECT_DIR / "strategy_log.json"
STATS_FILE = KITTY_PROJECT_DIR / "stats.json"
ROUTER_LOG_FILE = KITTY_PROJECT_DIR / "router_log.json"
MODEL_PREFS_FILE = KITTY_PROJECT_DIR / "model_preferences.json"

load_dotenv(dotenv_path=ENV_PATH)
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

# --- Bytez SDK Integration ---
# Never hardcode credentials. If unset, runtime components should degrade gracefully.
BYTEZ_KEY = os.getenv("BYTEZ_API_KEY", "").strip()
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

# --- Responsive Config ---
MAX_WIDTH = 85 

# --- Runtime Mode Config ---
class RuntimeConfig:
    """Singleton runtime configuration toggled by CLI flags."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.strict_mode = False
            cls._instance.theme = "catgirl"
        return cls._instance
    
    @property
    def temperature(self):
        return 0.1 if self.strict_mode else 0.7
    
    @property
    def persona_enabled(self):
        return not self.strict_mode
