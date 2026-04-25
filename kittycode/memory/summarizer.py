import logging

from kittycode.utils.helpers import extract_content

logger = logging.getLogger(__name__)

SUMMARIZE_PROMPT = """
Compress the following conversation into a single concise paragraph.
Preserve: key decisions, tool actions taken, file names, user preferences, and goals.
Discard: filler, greetings, repeated information.
Output ONLY the summary paragraph, nothing else.
"""

class Summarizer:
    """Compresses older conversation history into a compact context block."""

    def __init__(self, router=None):
        self.router = router

    def summarize(self, messages: list) -> str:
        """
        Summarizes a list of message dicts into a compact paragraph.
        Falls back to truncation if model call fails or router is None.
        """
        if not messages:
            return ""

        # Build a text block from messages
        text_block = self._messages_to_text(messages)

        # If no router available, fall back to truncation
        if not self.router:
            return self._truncate_fallback(text_block)

        try:
            prompt = [
                {"role": "system", "content": SUMMARIZE_PROMPT},
                {"role": "user", "content": text_block}
            ]
            result, _ = self.router.generate(prompt, task_type="Thought")
            summary = extract_content(result.output).strip()
            if summary and len(summary) > 10:
                return summary
            # If summary is garbage, fall back
            return self._truncate_fallback(text_block)
        except Exception as e:
            logger.warning(f"Summarization failed, using truncation fallback: {e}")
            return self._truncate_fallback(text_block)

    def _messages_to_text(self, messages: list) -> str:
        lines = []
        for m in messages:
            role = m.get("role", "unknown").upper()
            content = m.get("content", "")
            # Truncate very long individual messages
            if len(content) > 500:
                content = content[:500] + "..."
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _truncate_fallback(self, text: str, max_chars=800) -> str:
        """Simple truncation when model summarization is unavailable."""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "... [truncated]"


