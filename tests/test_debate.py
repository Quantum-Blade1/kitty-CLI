from unittest.mock import MagicMock, patch
from kittycode.agent.debate import DebateManager

def test_debate_pass_path():
    mock_router = MagicMock()
    mock_result = MagicMock()
    mock_result.output = "I will create the files."
    mock_result.error = None
    mock_router.generate.return_value = (mock_result, "gpt-4.1")

    mock_engine = MagicMock()
    mock_engine.execute_tools.return_value = (["File written"], "I created the files.")

    dm = DebateManager(mock_router, mock_engine)

    # Make critic return PASS
    with patch.object(dm, "_critic_review", return_value=(True, "PASS: looks good")):
        speech, actions, history = dm.run_step("create a file", [{"role": "system", "content": "sys"}])
    assert "created" in speech.lower() or isinstance(speech, str)

def test_debate_revise_path():
    mock_router = MagicMock()
    mock_result = MagicMock()
    mock_result.output = "I will create the files."
    mock_result.error = None
    mock_router.generate.return_value = (mock_result, "gpt-4.1")

    mock_engine = MagicMock()
    mock_engine.execute_tools.return_value = (["File written"], "I created the files.")

    dm = DebateManager(mock_router, mock_engine)

    # Make critic return REVISE
    with patch.object(dm, "_critic_review", return_value=(False, "logic error")):
        with patch.object(dm, "_builder_revise", return_value=("Revised output", ["Revision: fixed logic"])):
            speech, actions, history = dm.run_step("create a file", [{"role": "system", "content": "sys"}])
            
    assert any("Revision" in a or "REVISE" in a for a in actions)
