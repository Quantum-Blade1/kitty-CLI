from typer.testing import CliRunner

from kittycode.cli.app import app


runner = CliRunner()


def test_help_includes_stage3_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for token in ["doctor", "models", "memory", "stats", "chat", "run", "config", "version"]:
        assert token in result.stdout


def test_json_doctor_output_is_valid():
    result = runner.invoke(app, ["--json", "doctor"])
    # doctor can return 0 or 2 depending on machine state; both are contract-valid
    assert result.exit_code in (0, 2)
    assert "\"checks\"" in result.stdout
    assert "\"critical_failed\"" in result.stdout
