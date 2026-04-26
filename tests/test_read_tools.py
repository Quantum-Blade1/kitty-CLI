"""Tests for kittycode/tools/read_tools.py"""

import os
import textwrap
import pytest
from kittycode.tools.read_tools import action_read_file, action_grep, action_find_symbol


def test_read_file_returns_line_numbers(tmp_path):
    """read_file should return file contents prefixed with 1-indexed line numbers."""
    content = "alpha\nbeta\ngamma\ndelta\nepsilon\n"
    f = tmp_path / "sample.txt"
    f.write_text(content, encoding="utf-8")

    result = action_read_file(str(f))

    # Every content line should have " | " separating lineno from text
    lines = result.split("\n")
    # First line is the header
    assert "sample.txt" in lines[0]
    assert "(5 lines)" in lines[0]

    # Content lines start at index 1
    for i in range(1, 6):
        assert f"{i} | " in lines[i], f"Line {i} missing number prefix"

    # Verify content is intact
    assert "alpha" in result
    assert "epsilon" in result


def test_read_file_range(tmp_path):
    """read_file with start_line and end_line should return only that range."""
    lines_content = "\n".join(f"line_{i}" for i in range(1, 21))
    f = tmp_path / "ranged.txt"
    f.write_text(lines_content, encoding="utf-8")

    result = action_read_file(str(f), start_line=5, end_line=8)

    assert "showing lines 5-8" in result
    assert "line_5" in result
    assert "line_8" in result
    assert "line_4" not in result
    assert "line_9" not in result


def test_read_file_not_found(tmp_path):
    """read_file should return an error string for missing files, not raise."""
    result = action_read_file(str(tmp_path / "nonexistent.py"))
    assert "Error" in result
    assert "not found" in result


def test_grep_finds_pattern(tmp_path):
    """grep should find a unique string in exactly one of two files."""
    (tmp_path / "a.py").write_text("def hello():\n    pass\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def world():\n    pass\n", encoding="utf-8")

    result = action_grep("hello", path=str(tmp_path))

    assert "a.py" in result
    assert "hello" in result
    # b.py should NOT appear (it doesn't contain "hello")
    assert "b.py" not in result


def test_grep_no_matches(tmp_path):
    """grep should return 'No matches found.' when nothing matches."""
    (tmp_path / "empty.py").write_text("nothing here\n", encoding="utf-8")

    result = action_grep("zzz_nonexistent_pattern", path=str(tmp_path))
    assert result == "No matches found."


def test_grep_invalid_regex():
    """grep should return an error for invalid regex, not crash."""
    result = action_grep("[invalid(")
    assert "Error" in result
    assert "Invalid regex" in result


def test_find_symbol_locates_function(tmp_path):
    """find_symbol should locate a function definition."""
    code = textwrap.dedent("""\
        import os

        def foo():
            return 42

        def bar():
            return foo() + 1

        class Baz:
            pass
    """)
    (tmp_path / "module.py").write_text(code, encoding="utf-8")

    result = action_find_symbol("foo", path=str(tmp_path))

    assert "module.py" in result
    assert "def foo" in result
    # Line 3 is where 'def foo():' lives
    assert ":3:" in result


def test_find_symbol_locates_class(tmp_path):
    """find_symbol should locate class definitions."""
    code = "class MyEngine:\n    pass\n"
    (tmp_path / "eng.py").write_text(code, encoding="utf-8")

    result = action_find_symbol("MyEngine", path=str(tmp_path))
    assert "eng.py" in result
    assert "class MyEngine" in result


def test_find_symbol_not_found(tmp_path):
    """find_symbol should return 'No definitions found' when symbol doesn't exist."""
    (tmp_path / "empty.py").write_text("x = 1\n", encoding="utf-8")

    result = action_find_symbol("nonexistent_symbol_xyz", path=str(tmp_path))
    assert "No definitions found" in result
