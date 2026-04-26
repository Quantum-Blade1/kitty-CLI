"""
History Manager — 5-stage context compaction pipeline.
"""

import logging
from kittycode.memory.summarizer import Summarizer

logger = logging.getLogger(__name__)

class HistoryManager:
    """
    Manages conversation history with a multi-stage compaction pipeline
    to handle long-running autonomous tasks efficiently.
    """

    def __init__(self, router=None, window_size=10, enable_summarization=True):
        self.window_size = window_size
        self.enable_summarization = enable_summarization
        self.summarizer = Summarizer(router=router)
        self._running_summary = ""

    def _estimate_tokens(self, messages: list) -> int:
        """Rough but fast estimation: 1 token ≈ 4 characters."""
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        return total_chars // 4

    def trim(self, history: list) -> list:
        """
        Processes history through the 5-stage compaction pipeline.
        """
        if not history:
            return []

        h = list(history)  # Work on a copy

        # Stage 1: BUDGET REDUCTION
        h = self._stage_1_budget_reduction(h)

        # Stage 2: SNIP
        h = self._stage_2_snip(h)

        # Stage 3: MICROCOMPACT
        h = self._stage_3_microcompact(h)

        # Stage 4: CONTEXT COLLAPSE
        h = self._stage_4_context_collapse(h)

        # Stage 5: AUTO-COMPACT GUARD
        h = self._stage_5_auto_compact_guard(h)

        return h

    def _stage_1_budget_reduction(self, history: list) -> list:
        """Remove low-value or duplicate tool results."""
        if len(history) <= 5:
            return history

        new_history = [history[0]] # Always keep system prompt
        low_value_patterns = {"No changes", "Working tree clean", "No matches found.", "No changes."}
        
        for i in range(1, len(history)):
            msg = history[i]
            content = str(msg.get("content", "")).strip()
            
            # Keep the last 4 messages regardless
            if i >= len(history) - 4:
                new_history.append(msg)
                continue

            # Drop low-value tool results
            if content in low_value_patterns:
                continue

            # Drop duplicate consecutive tool results (simplified check)
            if i > 1:
                prev_content = str(history[i-1].get("content", "")).strip()
                if content == prev_content and content.startswith("[TOOL RESULTS]"):
                    continue

            new_history.append(msg)
        
        return new_history

    def _stage_2_snip(self, history: list) -> list:
        """Truncate extremely long messages in the middle of history."""
        for i in range(1, len(history) - 6): # Skip system prompt and last 6
            msg = history[i]
            content = str(msg.get("content", ""))
            if len(content) > 2000:
                snip_len = len(content) - 1200
                new_content = content[:1000] + f"\n...[snipped {snip_len} chars]...\n" + content[-200:]
                msg["content"] = new_content
        return history

    def _stage_3_microcompact(self, history: list) -> list:
        """Summarize oldest 30% if over 12k tokens."""
        if self._estimate_tokens(history) < 12000:
            return history

        system_prompt = history[0]
        conversation = history[1:]
        
        evict_count = int(len(conversation) * 0.3)
        if evict_count < 2:
            return history

        to_summarize = conversation[:evict_count]
        remaining = conversation[evict_count:]
        
        summary = self.summarizer.summarize(to_summarize)
        summary_msg = {"role": "system", "content": f"[MICROCOMPACT SUMMARY]\n{summary}"}
        
        return [system_prompt, summary_msg] + remaining

    def _stage_4_context_collapse(self, history: list) -> list:
        """Emergency collapse: summarize entire history if over 24k tokens."""
        if self._estimate_tokens(history) < 24000:
            return history

        logger.warning("Context collapsed — history too long.")
        system_prompt = history[0]
        conversation = history[1:]
        
        if len(conversation) <= 3:
            return history

        to_summarize = conversation[:-2]
        last_two = conversation[-2:]
        
        summary = self.summarizer.summarize(to_summarize)
        summary_msg = {"role": "system", "content": f"[CONTEXT COLLAPSED]\n{summary}"}
        
        return [system_prompt, summary_msg] + last_two

    def _stage_5_auto_compact_guard(self, history: list) -> list:
        """Hard safety ceiling: truncate to last 20 if still over 32k tokens."""
        if self._estimate_tokens(history) < 32000:
            return history

        logger.error("Auto-compact guard triggered — emergency truncation to 20 messages.")
        system_prompt = history[0]
        return [system_prompt] + history[-19:]

    def reset(self):
        self._running_summary = ""
