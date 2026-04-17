import json

from typer.testing import CliRunner

from kittycode.cli.app import app


runner = CliRunner()


def test_stats_json_includes_command_metrics():
    v = runner.invoke(app, ["--json", "version"])
    assert v.exit_code == 0

    s = runner.invoke(app, ["--json", "stats"])
    assert s.exit_code == 0
    payload = json.loads(s.stdout)
    assert payload["ok"] is True
    summary = payload["summary"]
    assert "command_calls" in summary
    assert "avg_command_latency_s" in summary


def test_doctor_json_includes_remediation_suggestions():
    d = runner.invoke(app, ["--json", "doctor"])
    assert d.exit_code in (0, 2)
    payload = json.loads(d.stdout)
    assert "remediation_suggestions" in payload
    assert isinstance(payload["remediation_suggestions"], list)
