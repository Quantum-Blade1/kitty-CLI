import json
import importlib.util
import logging
from kittycode.config.settings import KITTY_PROJECT_DIR

logger = logging.getLogger(__name__)

PLUGINS_DIR = KITTY_PROJECT_DIR / "plugins"

REQUIRED_MANIFEST_KEYS = {"name", "version", "tools", "permissions"}

def load_plugins(registry):
    """
    Scans .kitty/plugins/ for plugin folders.
    Each plugin must contain manifest.json and tool.py.
    Tools are registered into the shared ToolRegistry with sandbox restrictions.
    """
    if not PLUGINS_DIR.exists():
        PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        return []

    loaded = []
    
    for plugin_dir in PLUGINS_DIR.iterdir():
        if not plugin_dir.is_dir():
            continue
            
        manifest_path = plugin_dir / "manifest.json"
        tool_path = plugin_dir / "tool.py"
        
        if not manifest_path.exists() or not tool_path.exists():
            logger.warning(f"Plugin '{plugin_dir.name}' missing manifest.json or tool.py — skipped.")
            continue
        
        try:
            # Load and validate manifest
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
            
            missing = REQUIRED_MANIFEST_KEYS - set(manifest.keys())
            if missing:
                logger.warning(f"Plugin '{plugin_dir.name}' manifest missing keys: {missing} — skipped.")
                continue
            
            # Dynamically load tool.py as a module
            spec = importlib.util.spec_from_file_location(
                f"kitty_plugin_{manifest['name']}", str(tool_path)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # The tool.py must expose a `register(registry)` function
            if not hasattr(module, "register"):
                logger.warning(f"Plugin '{manifest['name']}' tool.py has no register() function — skipped.")
                continue
            
            # Call the plugin's register function with our ToolRegistry
            module.register(registry)
            
            loaded.append({
                "name": manifest["name"],
                "version": manifest["version"],
                "tools": manifest["tools"],
                "permissions": manifest["permissions"]
            })
            
            logger.info(f"Loaded plugin: {manifest['name']} v{manifest['version']} ({len(manifest['tools'])} tools)")
            
        except Exception as e:
            logger.error(f"Failed to load plugin '{plugin_dir.name}': {e}")
            continue
    
    return loaded
