import logging
from kittycode.memory.summarizer import Summarizer

logger = logging.getLogger(__name__)

WINDOW_SIZE = 10  # Keep last N user/assistant message pairs

class HistoryManager:
    """
    Manages conversation history with a sliding window.
    
    Structure after trimming:
    [system_prompt, context_summary_message, ...last_N_messages]
    
    Older messages beyond the window are summarized into a single
    context block injected right after the system prompt.
    """

    def __init__(self, router=None, window_size=WINDOW_SIZE, enable_summarization=True):
        self.window_size = window_size
        self.enable_summarization = enable_summarization
        self.summarizer = Summarizer(router=router)
        self._running_summary = ""  # Accumulated context from previous trims

    def trim(self, history: list) -> list:
        """
        Trims history to: [system_prompt] + [context_summary] + [last N messages].
        Summarizes evicted messages and accumulates into running context.
        Returns the trimmed history list.
        """
        if len(history) <= self.window_size + 1:
            # +1 for system prompt — nothing to trim
            return history

        # Separate system prompt from conversation
        system_prompt = history[0] if history and history[0].get("role") == "system" else None
        conversation = history[1:] if system_prompt else history

        # Check if there's already a context summary message (from previous trim)
        has_existing_summary = (
            len(conversation) > 0
            and conversation[0].get("role") == "system"
            and conversation[0].get("content", "").startswith("[CONTEXT SUMMARY]")
        )

        if has_existing_summary:
            # Skip the existing summary message in conversation
            conversation = conversation[1:]

        # Split into evictable and window
        if len(conversation) <= self.window_size:
            # Nothing to evict after removing summary
            result = [system_prompt] if system_prompt else []
            if self._running_summary:
                result.append(self._make_summary_message(self._running_summary))
            result.extend(conversation)
            return result

        evict_count = len(conversation) - self.window_size
        to_evict = conversation[:evict_count]
        to_keep = conversation[evict_count:]

        # Summarize evicted messages
        if self.enable_summarization and to_evict:
            new_summary = self.summarizer.summarize(to_evict)
            if self._running_summary:
                # Merge with existing accumulated summary
                self._running_summary = self.summarizer.summarize([
                    {"role": "system", "content": self._running_summary},
                    {"role": "user", "content": new_summary}
                ])
            else:
                self._running_summary = new_summary
        elif to_evict:
            # Summarization disabled — just truncate
            fallback = self.summarizer._truncate_fallback(
                self.summarizer._messages_to_text(to_evict)
            )
            self._running_summary = (
                self._running_summary + "\n" + fallback
                if self._running_summary else fallback
            )

        # Rebuild history
        result = []
        if system_prompt:
            result.append(system_prompt)
        if self._running_summary:
            result.append(self._make_summary_message(self._running_summary))
        result.extend(to_keep)

        logger.info(f"History trimmed: evicted {evict_count} messages, window={len(to_keep)}")
        return result

    def _make_summary_message(self, summary: str) -> dict:
        return {
            "role": "system",
            "content": f"[CONTEXT SUMMARY] Previous conversation context:\n{summary}"
        }

    def reset(self):
        """Clears accumulated summary (e.g., on new conversation)."""
        self._running_summary = ""
