import json
from kittycode.config.settings import HEALTH_FILE
from kittycode.telemetry.logger import get_logger
logger = get_logger("models.health")

CONSECUTIVE_FAIL_THRESHOLD = 3
LATENCY_THRESHOLD_S = 30.0

class ModelHealthTracker:
    """Tracks per-model health with consecutive failure counting, latency stats, and session demotion."""
    
    def __init__(self):
        self.health_file = HEALTH_FILE
        self.stats = self._load()
        self._dirty = False  # Dirty flag — only write to disk on flush()
        self._session_demoted = set()

    def _load(self):
        if self.health_file.exists():
            try:
                with open(self.health_file, "r") as f: return json.load(f)
            except: pass
        return {}

    def _save(self):
        """Writes to disk only if data has changed."""
        if not self._dirty:
            return
        try:
            with open(self.health_file, "w") as f: json.dump(self.stats, f, indent=4)
            self._dirty = False
        except: pass

    def flush(self):
        """Alias for _save() — called once per REPL cycle."""
        self._save()

    def _init_model(self, model_id: str):
        defaults = {
            "success": 0,
            "failures": 0,
            "consecutive_failures": 0,
            "total_latency": 0.0,
            "call_count": 0,
            "status": "active"
        }
        if model_id not in self.stats:
            self.stats[model_id] = defaults.copy()
        else:
            # Backfill any missing keys from schema upgrades
            for key, val in defaults.items():
                if key not in self.stats[model_id]:
                    self.stats[model_id][key] = val

    def record_success(self, model_id: str, latency: float = 0.0):
        self._init_model(model_id)
        s = self.stats[model_id]
        s["success"] += 1
        s["consecutive_failures"] = 0  # Reset streak on success
        s["status"] = "active"
        s["total_latency"] += latency
        s["call_count"] += 1
        
        self._session_demoted.discard(model_id)
        self._dirty = True  # Mark dirty — flushed at end of cycle

    def record_failure(self, model_id: str):
        self._init_model(model_id)
        s = self.stats[model_id]
        s["failures"] += 1
        s["consecutive_failures"] += 1
        
        # Auto-demote after consecutive threshold
        if s["consecutive_failures"] >= CONSECUTIVE_FAIL_THRESHOLD:
            s["status"] = "degraded"
            self._session_demoted.add(model_id)
            logger.warning(f"Model {model_id} demoted after {CONSECUTIVE_FAIL_THRESHOLD} consecutive failures.")
            
        self._dirty = True  # Mark dirty — flushed at end of cycle

    def record_high_latency(self, model_id: str):
        """Demote for current session if latency threshold exceeded."""
        self._session_demoted.add(model_id)
        logger.warning(f"Model {model_id} session-demoted due to high latency (>{LATENCY_THRESHOLD_S}s).")

    def is_healthy(self, model_id: str) -> bool:
        self._init_model(model_id)
        if model_id in self._session_demoted:
            return False
        return self.stats[model_id]["status"] != "degraded"

    def get_success_rate(self, model_id: str) -> float:
        self._init_model(model_id)
        s = self.stats[model_id]
        total = s["success"] + s["failures"]
        if total == 0: return 1.0
        return round(s["success"] / total, 3)

    def get_avg_latency(self, model_id: str) -> float:
        self._init_model(model_id)
        s = self.stats[model_id]
        if s["call_count"] == 0: return 0.0
        return round(s["total_latency"] / s["call_count"], 3)

    def get_health_score(self, model_id: str) -> float:
        """Composite score: 60% success rate + 40% inverse latency penalty."""
        sr = self.get_success_rate(model_id)
        avg_lat = self.get_avg_latency(model_id)
        latency_score = max(0, 1.0 - (avg_lat / LATENCY_THRESHOLD_S))
        return round(sr * 0.6 + latency_score * 0.4, 3)
        
    def reset_health(self):
        for m in self.stats:
            self.stats[m]["consecutive_failures"] = 0
            self.stats[m]["failures"] = 0
            self.stats[m]["status"] = "active"
        self._session_demoted.clear()
        self._dirty = True
        self._save()  # Reset is explicit — flush immediately
