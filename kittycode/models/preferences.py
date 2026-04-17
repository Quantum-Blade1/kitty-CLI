import json
from typing import Dict, List

from kittycode.config.settings import MODEL_PREFS_FILE
from kittycode.models.registry import DEFAULT_TASK_PREFERENCES, MODEL_REGISTRY, TASK_PREFERENCES


def _clone_defaults() -> Dict[str, Dict[str, List[str]]]:
    return {
        task: {"primary": cfg["primary"][:], "fallback": cfg["fallback"][:]}
        for task, cfg in DEFAULT_TASK_PREFERENCES.items()
    }


def get_preferences() -> Dict[str, Dict[str, List[str]]]:
    return {
        task: {"primary": cfg["primary"][:], "fallback": cfg["fallback"][:]}
        for task, cfg in TASK_PREFERENCES.items()
    }


def apply_preferences(prefs: Dict[str, Dict[str, List[str]]]) -> None:
    for task in list(TASK_PREFERENCES.keys()):
        cfg = prefs.get(task, {})
        primary = [m for m in cfg.get("primary", []) if m in MODEL_REGISTRY]
        fallback = [m for m in cfg.get("fallback", []) if m in MODEL_REGISTRY and m not in primary]
        if not primary:
            defaults = DEFAULT_TASK_PREFERENCES[task]
            primary = defaults["primary"][:]
            fallback = [m for m in defaults["fallback"] if m not in primary]
        TASK_PREFERENCES[task]["primary"] = primary
        TASK_PREFERENCES[task]["fallback"] = fallback


def load_preferences() -> Dict[str, Dict[str, List[str]]]:
    if not MODEL_PREFS_FILE.exists():
        prefs = _clone_defaults()
        apply_preferences(prefs)
        return get_preferences()
    try:
        with open(MODEL_PREFS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Invalid model preference file")
        apply_preferences(data)
        return get_preferences()
    except Exception:
        prefs = _clone_defaults()
        apply_preferences(prefs)
        return get_preferences()


def save_preferences() -> Dict[str, Dict[str, List[str]]]:
    prefs = get_preferences()
    with open(MODEL_PREFS_FILE, "w", encoding="utf-8") as f:
        json.dump(prefs, f, indent=2)
    return prefs


def set_primary_model(model_key: str, persist: bool = False) -> Dict[str, Dict[str, List[str]]]:
    if model_key not in MODEL_REGISTRY:
        raise ValueError(f"Unknown model: {model_key}")
    all_models = list(MODEL_REGISTRY.keys())
    fallbacks = [m for m in all_models if m != model_key]
    for task in ["Code", "Chat", "Thought"]:
        TASK_PREFERENCES[task]["primary"] = [model_key]
        TASK_PREFERENCES[task]["fallback"] = fallbacks
    return save_preferences() if persist else get_preferences()


def reset_preferences(persist: bool = False) -> Dict[str, Dict[str, List[str]]]:
    apply_preferences(_clone_defaults())
    return save_preferences() if persist else get_preferences()
