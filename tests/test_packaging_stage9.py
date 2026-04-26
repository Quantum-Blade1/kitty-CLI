from pathlib import Path

import tomllib


def test_pyproject_has_cli_script():
    pyproject = Path("pyproject.toml")
    assert pyproject.exists()
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = data["project"]
    assert project["name"] == "kittycode-agent"

    assert "kitty" in project["scripts"]
    assert project["scripts"]["kitty"] == "kittycode.cli.app:app"


def test_release_workflow_exists():
    wf = Path(".github/workflows/release.yml")
    assert wf.exists()
