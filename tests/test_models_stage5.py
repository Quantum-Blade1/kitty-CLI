import json

from typer.testing import CliRunner

from kittycode.cli.app import app
from kittycode.models.preferences import get_preferences, reset_preferences, set_primary_model


runner = CliRunner()


def test_set_and_reset_preferences():
    original = get_preferences()
    set_primary_model("claude-haiku", persist=False)
    current = get_preferences()
    assert current["Code"]["primary"] == ["claude-haiku"]
    assert "claude-haiku" not in current["Code"]["fallback"]

    reset_preferences(persist=False)
    reset_now = get_preferences()
    assert "bytez-qwen-coder" in reset_now["Code"]["primary"]
    assert "gpt-4.1" in reset_now["Code"]["primary"]

    # restore prior state for isolation
    if original["Code"]["primary"] != reset_now["Code"]["primary"]:
        set_primary_model(original["Code"]["primary"][0], persist=False)


def test_models_json_reports_chain():
    result = runner.invoke(app, ["--json", "models", "--show-chain", "Code"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert isinstance(payload["configured_chain"], list)
    assert isinstance(payload["resolved_chain"], list)
    assert len(payload["configured_chain"]) >= 1
