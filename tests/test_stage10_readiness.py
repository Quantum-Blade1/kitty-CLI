import json

from typer.testing import CliRunner

from kittycode.cli.app import app


runner = CliRunner()


def test_readiness_json_contract():
    result = runner.invoke(app, ["--json", "readiness"])
    assert result.exit_code in (0, 2)
    payload = json.loads(result.stdout)
    assert "ok" in payload
    assert "checks" in payload
    assert isinstance(payload["checks"], list)
