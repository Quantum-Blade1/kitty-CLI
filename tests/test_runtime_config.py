from kittycode.config.runtime import has_critical_failures, run_environment_checks


def test_runtime_checks_shape():
    checks = run_environment_checks()
    assert len(checks) >= 5
    assert all(hasattr(c, "name") for c in checks)
    assert all(c.severity in {"critical", "warning"} for c in checks)


def test_critical_failure_flag_is_boolean():
    checks = run_environment_checks()
    result = has_critical_failures(checks)
    assert isinstance(result, bool)
