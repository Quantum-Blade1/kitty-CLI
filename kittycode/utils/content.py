"""Shared content extraction utilities for LLM response parsing."""


def extract_content(output):
    """
    Extracts the text content from an LLM provider response output.

    Handles all output shapes returned by providers:
    - Plain string (GeminiProvider, OpenRouterProvider MockResult)
    - List of dicts with 'content' key (Bytez multi-turn)
    - Single dict with 'content' key
    - Nested list (last element extraction)

    Returns the content as a string.
    """
    if isinstance(output, str):
        return output
    if isinstance(output, list) and len(output) > 0:
        output = output[-1]
    if isinstance(output, dict):
        return output.get("content", str(output))
    return str(output)
