import json
import uuid

from typer.testing import CliRunner

from kittycode.cli.app import app


runner = CliRunner()


def _json(result):
    return json.loads(result.stdout)


from unittest.mock import patch
from kittycode.memory.manager import MemoryManager

_shared_mm = MemoryManager()

@patch("kittycode.cli.app.get_memory_manager", return_value=_shared_mm)
def test_memory_add_and_find_json(mock_mm):
    uid = uuid.uuid4().hex
    key = f"stage4key{uid[:8]}"          # no underscores — clean token
    value = f"stage4 memory value {uid[:6]}"  # unique value

    add_res = runner.invoke(
        app,
        ["--json", "memory", "add", "--key", key, "--value", value, "--category", "features"],
    )
    assert add_res.exit_code == 0
    assert _json(add_res)["ok"] is True

    find_res = runner.invoke(app, ["--json", "memory", "find", value, "--limit", "5"])

    assert find_res.exit_code == 0
    find_payload = _json(find_res)
    assert find_payload["ok"] is True
    # set_fact stores text as "key: value" — match on the value substring
    print("PAYLOAD:", find_payload)
    assert any(value in m.get("text", "") for m in find_payload["results"])


def test_memory_prune_and_export_json():
    prune_res = runner.invoke(app, ["--json", "memory", "prune", "--max", "200", "--dedupe"])
    assert prune_res.exit_code == 0
    prune_payload = _json(prune_res)
    assert prune_payload["ok"] is True
    assert "before" in prune_payload and "after" in prune_payload

    export_path = f"memory_export_{uuid.uuid4().hex[:8]}.json"
    export_res = runner.invoke(app, ["--json", "memory", "export", "--path", export_path])
    assert export_res.exit_code == 0
    export_payload = _json(export_res)
    assert export_payload["ok"] is True
    assert export_payload["path"].endswith(export_path)
