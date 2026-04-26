"""
Integration tests for KittyCode autonomous coding.
"""

import pytest
from unittest.mock import MagicMock, patch
from kittycode.agent.kitty import KittyAgent, StopReason

def test_agent_writes_and_reads_file(tmp_path, monkeypatch):
    """Full agent turn: write a file, then read it back."""
    monkeypatch.chdir(tmp_path)
    
    # Mock the LLM to return a write tool call, then a read tool call, then done
    responses = [
        '[{"tool":"write_raw","args":{"path":"hello.py","content":"print(1)"}}]',
        '[{"tool":"read_file","args":{"path":"hello.py"}}]',
        "TASK COMPLETE: wrote and verified hello.py"
    ]
    
    call_count = 0
    
    def mock_generate(prompt, task_type="Code"):
        nonlocal call_count
        r = MagicMock()
        r.output = responses[min(call_count, len(responses)-1)]
        r.error = None
        call_count += 1
        return r, "mock-model"

    # Important: SandboxValidator uses PROJECT_ROOT from settings.
    import kittycode.config.settings
    import kittycode.security.sandbox
    
    # We patch the default validator to point to our tmp_path
    new_validator = kittycode.security.sandbox.SandboxValidator(root=tmp_path)
    
    with patch("kittycode.config.settings.PROJECT_ROOT", tmp_path):
        with patch("kittycode.security.sandbox.get_validator", return_value=new_validator):
            with patch("kittycode.security.sandbox.get_default_validator", return_value=new_validator):
                # Patch ModelRouter.generate which is called by KittyAgent.run_task -> llm.router.generate
                with patch("kittycode.models.router.ModelRouter.generate", side_effect=mock_generate):
                    agent = KittyAgent()
                    result = agent.run_task("write hello.py")




    assert (tmp_path / "hello.py").exists()
    assert (tmp_path / "hello.py").read_text(encoding="utf-8").strip() == "print(1)"
    assert result["stop_reason"] == StopReason.TASK_COMPLETE
    assert result["iterations"] == 3
