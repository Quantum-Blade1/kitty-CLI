import json
import logging
from kittycode.config.settings import STATS_FILE

logger = logging.getLogger(__name__)

class StatsManager:
    """Lightweight, project-scoped metrics tracker for KittyCode observability."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.stats_file = STATS_FILE
        self._dirty = False  # Dirty flag — only write to disk on flush()
        self._data = {
            "model_calls": {},
            "total_latency": 0.0,
            "call_count": 0,
            "command_calls": {},
            "command_failures": 0,
            "command_total_latency": 0.0,
            "tool_executions": 0,
            "planner_tasks": 0,
            "reflections": 0,
            "memory_vector_size": 0,
        }
        self._load()

    def _load(self):
        if self.stats_file.exists():
            try:
                with open(self.stats_file, "r") as f:
                    saved = json.load(f)
                    self._data.update(saved)
            except Exception as e:
                logger.warning(f"Could not load stats: {e}")

    def save(self):
        """Writes to disk only if data has changed since last save."""
        if not self._dirty:
            return
        try:
            with open(self.stats_file, "w") as f:
                json.dump(self._data, f, indent=4)
            self._dirty = False
        except Exception as e:
            logger.warning(f"Could not save stats: {e}")

    def flush(self):
        """Alias for save() — called once per REPL cycle."""
        self.save()

    # --- Recording Methods (mark dirty, no disk write) ---

    def record_model_call(self, model_key: str, latency: float):
        """Record a model invocation with its latency."""
        self._data["model_calls"][model_key] = self._data["model_calls"].get(model_key, 0) + 1
        self._data["total_latency"] += latency
        self._data["call_count"] += 1
        self._dirty = True

    def record_command_call(self, command_name: str, latency: float, ok: bool):
        entry = self._data["command_calls"].get(command_name, {"count": 0, "failures": 0})
        entry["count"] += 1
        if not ok:
            entry["failures"] += 1
            self._data["command_failures"] += 1
        self._data["command_calls"][command_name] = entry
        self._data["command_total_latency"] += latency
        self._dirty = True

    def record_tool_exec(self):
        self._data["tool_executions"] += 1
        self._dirty = True

    def record_planner_task(self):
        self._data["planner_tasks"] += 1
        self._dirty = True

    def record_reflection(self):
        self._data["reflections"] += 1
        self._dirty = True

    def set_memory_size(self, n: int):
        self._data["memory_vector_size"] = n
        self._dirty = True

    # --- Query Methods ---

    def get_avg_latency(self) -> float:
        if self._data["call_count"] == 0:
            return 0.0
        return round(self._data["total_latency"] / self._data["call_count"], 3)

    def get_model_usage(self) -> dict:
        total = sum(self._data["model_calls"].values()) or 1
        return {k: round((v / total) * 100, 1) for k, v in self._data["model_calls"].items()}

    def get_avg_command_latency(self) -> float:
        total = sum(v.get("count", 0) for v in self._data.get("command_calls", {}).values())
        if total == 0:
            return 0.0
        return round(self._data["command_total_latency"] / total, 3)

    def get_summary(self) -> dict:
        return {
            "model_calls": self._data["model_calls"],
            "model_usage_pct": self.get_model_usage(),
            "total_calls": self._data["call_count"],
            "avg_latency_s": self.get_avg_latency(),
            "command_calls": self._data["command_calls"],
            "command_failures": self._data["command_failures"],
            "avg_command_latency_s": self.get_avg_command_latency(),
            "tool_executions": self._data["tool_executions"],
            "planner_tasks": self._data["planner_tasks"],
            "reflections": self._data["reflections"],
            "memory_vector_size": self._data["memory_vector_size"],
        }
