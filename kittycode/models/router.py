import json
import time
from typing import Any, List, Tuple

from kittycode.config.settings import BYTEZ_KEY, GEMINI_KEY, OPENROUTER_KEY, ROUTER_LOG_FILE
from kittycode.models.health import LATENCY_THRESHOLD_S, ModelHealthTracker
from kittycode.models.policy import build_routing_chain
from kittycode.models.preferences import load_preferences
from kittycode.models.providers import BytezProvider, GeminiProvider, OpenRouterProvider
from kittycode.models.registry import MODEL_REGISTRY, TASK_PREFERENCES
from kittycode.telemetry.logger import get_logger
from kittycode.utils.stats import StatsManager

log = get_logger("models.router")


class ModelRouter:
    def __init__(self):
        self.health = ModelHealthTracker()
        self._router_log = self._load_router_log()
        self._router_dirty = False

        # Provider dispatch registry — single source of truth
        self._providers = {
            "bytez":     BytezProvider(BYTEZ_KEY),
            "google":    GeminiProvider(GEMINI_KEY),
            "openai":    OpenRouterProvider(OPENROUTER_KEY),
            "anthropic": OpenRouterProvider(OPENROUTER_KEY),
            "deepseek":  OpenRouterProvider(OPENROUTER_KEY),
            "meta":      OpenRouterProvider(OPENROUTER_KEY),
        }

        self._current_prefs = load_preferences()

    # --- Provider Resolution ---

    def _resolve_provider(self, provider_name: str):
        """Resolve the active provider for a given provider name, with fallback chain."""
        p = self._providers.get(provider_name)
        if p and p.has_client():
            return p
        # fallback chain
        for name in ("openai", "bytez"):
            fb = self._providers.get(name)
            if fb and fb.has_client():
                return fb
        return None

    # --- Router Decision Log ---

    def _load_router_log(self) -> list:
        if ROUTER_LOG_FILE.exists():
            try:
                with open(ROUTER_LOG_FILE, "r", encoding="utf-8") as f:
                    logs = json.load(f)
                return logs[-100:] if len(logs) > 100 else logs
            except Exception:
                pass
        return []

    def _save_router_log(self):
        if not self._router_dirty:
            return
        try:
            with open(ROUTER_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._router_log[-100:], f, indent=2)
            self._router_dirty = False
        except Exception:
            pass

    def flush_log(self):
        self._save_router_log()

    def _log_decision(self, task_type: str, chain: list, chosen: str, reason: str, latency: float = 0.0):
        entry = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "task": task_type,
            "chain": chain,
            "chosen": chosen,
            "reason": reason,
            "latency": round(latency, 3),
        }
        self._router_log.append(entry)
        self._router_dirty = True

    # --- Adaptive Routing Chain ---

    def _get_routing_chain(self, task_type: str) -> List[str]:
        from kittycode.quantum.router_q import quantum_select

        prefs = TASK_PREFERENCES.get(task_type, TASK_PREFERENCES["Chat"])
        base_list = prefs["primary"] + prefs["fallback"]

        # Deterministic health gate first (remove degraded models)
        viable = build_routing_chain(base_list, self.health)

        # Quantum-inspired ordering of viable models
        return quantum_select(viable, self.health, task_type, self._router_log)

    # --- Confidence Check ---

    def _check_output_confidence(self, result, task_type: str) -> bool:
        try:
            output = result.output
            # Handle all output shapes: str (Gemini/OpenRouter), list, dict (Bytez)
            if isinstance(output, str):
                content = output
            elif isinstance(output, list) and len(output) > 0:
                last = output[-1]
                content = last.get("content", str(last)) if isinstance(last, dict) else str(last)
            elif isinstance(output, dict):
                content = output.get("content", str(output))
            else:
                content = str(output) if output else ""
            if not content or not content.strip():
                return False
            if task_type == "Code" and len(content.strip()) < 5:
                return False
            return True
        except Exception:
            return False

    # --- Main generate() ---

    def generate(self, prompt: Any, task_type: str = "Chat") -> Tuple[Any, str]:
        from kittycode.config.settings import RuntimeConfig

        # Check that at least one provider is available
        if not any(p.has_client() for p in self._providers.values()):
            raise Exception("SDK not initialized. Check API Key.")

        config = RuntimeConfig()
        chain = self._get_routing_chain(task_type)
        last_error = None

        for model_key in chain:
            reg_info = MODEL_REGISTRY.get(model_key)
            if not reg_info:
                continue

            provider_name = reg_info.get("provider", "bytez")
            active_provider = self._resolve_provider(provider_name)

            if active_provider is None:
                last_error = Exception(f"No provider available for {model_key} (needs {provider_name})")
                log.warning("provider_unavailable", model=model_key, provider=provider_name)
                continue

            t0 = time.time()
            try:
                result = active_provider.run(reg_info["id"], prompt, params={"temperature": config.temperature})
                latency = time.time() - t0

                if hasattr(result, "error") and result.error:
                    raise Exception(f"API Error: {result.error}")

                if latency > LATENCY_THRESHOLD_S:
                    self.health.record_high_latency(model_key)
                    log.warning("model_slow", model=model_key, latency=round(latency, 1), threshold=LATENCY_THRESHOLD_S)
                    self._log_decision(task_type, chain, model_key, f"SLOW ({latency:.1f}s) - session-demoted", latency)

                if not self._check_output_confidence(result, task_type):
                    log.warning("low_confidence_output", model=model_key, task_type=task_type)
                    self.health.record_failure(model_key)
                    self._log_decision(task_type, chain, model_key, "LOW_CONFIDENCE - fallback triggered", latency)
                    continue

                self.health.record_success(model_key, latency)
                StatsManager().record_model_call(model_key, latency)
                log.info("model_success", model=model_key, task_type=task_type, latency=round(latency, 3))
                self._log_decision(task_type, chain, model_key, "SUCCESS", latency)
                return result, model_key

            except Exception as e:
                latency = time.time() - t0
                log.error("model_failed", model=model_key, task_type=task_type, error=str(e)[:100])
                self.health.record_failure(model_key)
                self._log_decision(task_type, chain, model_key, f"FAIL: {str(e)[:80]}", latency)
                last_error = e
                continue

        raise Exception(f"All models in routing chain failed for task {task_type}. Last error: {str(last_error)}")
