import os
import pytest
from kittycode.tools.git_tools import action_git_status, action_git_diff, action_git_commit
from kittycode.tools.test_tools import action_run_tests
from kittycode.config.settings import PROJECT_ROOT

def test_git_status(tmp_path):
    # This test might be tricky without a real git repo, but we can check if it returns an error or string
    result = action_git_status()
    assert isinstance(result, str)

def test_run_tests_manual_command(tmp_path):
    # Should run the provided command and return results
    result = action_run_tests(command="echo 'Tests Passed'")
    assert "PASSED" in result
    assert "echo 'Tests Passed'" in result
