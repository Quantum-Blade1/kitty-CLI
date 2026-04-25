import os


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')  # nosec B605


def extract_content(output) -> str:
    """Extracts text from any LLM provider result shape."""
    if isinstance(output, list) and output:
        output = output[-1]
    if isinstance(output, dict):
        return output.get("content", str(output))
    return str(output) if output is not None else ""
