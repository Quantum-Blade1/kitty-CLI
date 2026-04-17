import json

from typer.testing import CliRunner

import kittycode.cli.app as cli_app


runner = CliRunner()


def test_doctor_returns_nonzero_on_critical_failure(monkeypatch):
    class _Check:
        def __init__(self, name, ok, severity, detail, fix):
            self.name = name
            self.ok = ok
            self.severity = severity
            self.detail = detail
            self.fix = fix

    def fake_checks():
        return [_Check("bytez installed", False, "critical", "missing", "install requirements")]

    monkeypatch.setattr("kittycode.config.runtime.run_environment_checks", fake_checks)
    monkeypatch.setattr("kittycode.config.runtime.has_critical_failures", lambda checks: True)

    result = runner.invoke(cli_app.app, ["--json", "doctor"])
    assert result.exit_code == cli_app.EXIT_USAGE_ERROR
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["critical_failed"] is True


def test_models_invalid_primary_returns_usage_error():
    result = runner.invoke(cli_app.app, ["--json", "models", "--set-primary", "not-a-model"])
    assert result.exit_code == cli_app.EXIT_USAGE_ERROR
    payload = json.loads(result.stdout)
    assert payload["ok"] is False


def test_memory_invalid_category_returns_usage_error():
    result = runner.invoke(cli_app.app, ["--json", "memory", "--category", "bad_category"])
    assert result.exit_code == cli_app.EXIT_USAGE_ERROR
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
