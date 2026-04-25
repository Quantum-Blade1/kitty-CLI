from kittycode.security.policy import validate_command


def test_policy_allows_safe_command():
    ok, reason = validate_command("python --version")
    assert ok is True
    assert "Allowed" in reason


def test_policy_blocks_shell_operators():
    ok, reason = validate_command("python --version && whoami")
    assert ok is False
    assert "Blocked shell control token" in reason


def test_policy_allows_python_c_flag():
    ok, reason = validate_command('python -c "print(1)"')
    assert ok is True

