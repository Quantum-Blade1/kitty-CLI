"""
Structured JSON logging with per-interaction trace IDs for KittyCode.

Usage in any module:
    from kittycode.telemetry.logger import get_logger, new_trace

    log = get_logger("models.router")
    log.info("model_selected", model="deepseek-v3", latency=1.2)
    log.debug("routing_chain", chain=["deepseek-v3", "gpt-4o"])
    log.error("model_failed", model="llama-4", error="timeout")

Trace lifecycle:
    1. new_trace() called at start of each REPL interaction
    2. All log calls automatically include the current trace_id
    3. Trace resets on next user input
"""

import json
import logging
import uuid
import time
import threading
from kittycode.config.settings import KITTY_PROJECT_DIR

# --- Trace Context (thread-local for safety) ---
_trace_ctx = threading.local()

def new_trace() -> str:
    """Generate a new trace ID for the current interaction. Call once per REPL cycle."""
    trace_id = uuid.uuid4().hex[:12]
    _trace_ctx.trace_id = trace_id
    _trace_ctx.start_time = time.time()
    return trace_id

def get_trace_id() -> str:
    """Returns current trace ID, or 'no-trace' if none is set."""
    return getattr(_trace_ctx, "trace_id", "no-trace")

def get_trace_elapsed() -> float:
    """Returns seconds since trace started."""
    start = getattr(_trace_ctx, "start_time", None)
    return round(time.time() - start, 3) if start else 0.0


# --- JSON Formatter ---
class StructuredFormatter(logging.Formatter):
    """Formats log records as single-line JSON with trace context."""

    def format(self, record):
        entry = {
            "ts": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "trace_id": get_trace_id(),
            "module": record.name,
            "event": record.getMessage(),
        }
        # Merge any extra structured data passed via log.info("event", extra={...})
        details = getattr(record, "_structured", None)
        if details:
            entry["details"] = details
        return json.dumps(entry, default=str)


# --- Structured Logger Wrapper ---
class StructuredLogger:
    """
    Thin wrapper around stdlib logger that adds structured data support.
    
    Usage:
        log = get_logger("module_name")
        log.info("event_name", key1="val1", key2=42)
    """

    def __init__(self, name: str):
        self._logger = logging.getLogger(f"kitty.{name}")

    def info(self, event: str, **details):
        self._logger.info(event, extra={"_structured": details} if details else {})

    def debug(self, event: str, **details):
        self._logger.debug(event, extra={"_structured": details} if details else {})

    def warning(self, event: str, **details):
        self._logger.warning(event, extra={"_structured": details} if details else {})

    def error(self, event: str, **details):
        self._logger.error(event, extra={"_structured": details} if details else {})


# --- Setup ---
_initialized = False

LOG_FILE = KITTY_PROJECT_DIR / "kitty.log"

def setup_logging(debug: bool = False):
    """
    Configures the kitty.* logger hierarchy.
    Call once at startup from CLI entry point.
    
    - Always writes JSON logs to .kitty/kitty.log
    - In debug mode, also prints to stderr at DEBUG level
    - In normal mode, file logging at INFO level, no console output
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    root = logging.getLogger("kitty")
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    root.handlers.clear()

    # File handler — always active, JSON formatted
    file_handler = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
    file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    file_handler.setFormatter(StructuredFormatter())
    root.addHandler(file_handler)

    # Console handler — only in debug mode
    if debug:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(StructuredFormatter())
        root.addHandler(console_handler)


def get_logger(name: str) -> StructuredLogger:
    """Returns a StructuredLogger for the given module name."""
    return StructuredLogger(name)
