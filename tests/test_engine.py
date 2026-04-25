from kittycode.tools.registry import ToolRegistry
from kittycode.tools.engine import ToolEngine
from kittycode.tools.fs_tools import setup_fs_tools


def test_engine_blocks_path_traversal():
    registry = ToolRegistry()
    setup_fs_tools(registry)
    engine = ToolEngine(registry)

    test_json = """
```json
[{"tool": "mkdir", "args": {"path": "../malicious_folder"}}]
```
"""
    actions, _ = engine.execute_tools(test_json)
    text = " ".join(actions).lower()
    assert "denied" in text or "blocked" in text


def test_engine_allows_python_c_flag():
    """python -c is a legitimate pattern and must NOT be blocked after policy fix."""
    from unittest.mock import patch
    registry = ToolRegistry()
    setup_fs_tools(registry)
    engine = ToolEngine(registry)

    test_json = """
```json
[{"tool": "run_cmd", "args": {"command": "python -c \\"print(1)\\""}}]
```
"""
    with patch("kittycode.tools.engine.Confirm.ask", return_value=True):
        actions, _ = engine.execute_tools(test_json)
        
    text = " ".join(actions).lower()
    assert "blocked" not in text

