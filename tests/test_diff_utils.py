"""Tests for kittycode/utils/diff_utils.py and action_write_raw"""

import os
import pytest
from kittycode.utils.diff_utils import unified_diff
from kittycode.tools.fs_tools import action_write_raw


def test_unified_diff_shows_changes():
    """unified_diff should show additions and deletions."""
    old = "line1\nline2\n"
    new = "line1\nline3\n"
    diff = unified_diff(old, new, "test.txt")
    
    assert "-line2" in diff
    assert "+line3" in diff
    assert "@@" in diff


def test_unified_diff_empty_when_unchanged():
    """unified_diff should return empty string if contents match."""
    content = "same\n"
    diff = unified_diff(content, content, "test.txt")
    assert diff == ""


def test_write_no_diff_for_new_file(tmp_path):
    """action_write_raw should create a file without any prompts."""
    path = tmp_path / "new_file.txt"
    content = "hello world"
    
    result = action_write_raw(str(path), content)
    
    assert path.is_file()
    assert path.read_text(encoding="utf-8") == content
    assert "File Written" in result
