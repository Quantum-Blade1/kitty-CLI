"""Tests for kittycode/context/indexer.py"""

import os
import pytest
from pathlib import Path
from kittycode.context.indexer import CodebaseIndex


def test_build_creates_tree(tmp_path):
    """build should create a tree with the expected number of file entries."""
    # Create 5 files
    for i in range(5):
        (tmp_path / f"file_{i}.py").write_text("print('hello')", encoding="utf-8")
    
    # Create a subdir with 2 more files
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "subfile_1.py").write_text("print('sub')", encoding="utf-8")
    (subdir / "subfile_2.py").write_text("print('sub')", encoding="utf-8")

    index = CodebaseIndex(tmp_path, max_files=10).build()
    
    # Total files = 5 + 2 = 7
    files = [t for t in index._tree if t["type"] == "file"]
    assert len(files) == 7


def test_skips_pycache(tmp_path):
    """Indexer should skip __pycache__ and binary extensions."""
    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "foo.pyc").write_text("binary", encoding="utf-8")
    (tmp_path / "normal.py").write_text("print('hi')", encoding="utf-8")
    (tmp_path / "artifact.so").write_text("binary", encoding="utf-8")

    index = CodebaseIndex(tmp_path).build()
    
    paths = [t["path"] for t in index._tree]
    assert "normal.py" in paths
    assert "__pycache__" not in paths
    assert "foo.pyc" not in paths
    assert "artifact.so" not in paths


def test_marks_entry_points(tmp_path):
    """Indexer should tag entry points, configs, and docs."""
    (tmp_path / "main.py").write_text("entry", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("config", encoding="utf-8")
    (tmp_path / "README.md").write_text("doc", encoding="utf-8")
    (tmp_path / "other.py").write_text("other", encoding="utf-8")

    index = CodebaseIndex(tmp_path).build()
    
    main_entry = next(t for t in index._tree if t["name"] == "main.py")
    config_entry = next(t for t in index._tree if t["name"] == "pyproject.toml")
    doc_entry = next(t for t in index._tree if t["name"] == "README.md")
    other_entry = next(t for t in index._tree if t["name"] == "other.py")

    assert main_entry["is_entry"] is True
    assert config_entry["is_config"] is True
    assert doc_entry["is_doc"] is True
    assert other_entry["is_entry"] is False


def test_to_prompt_block_respects_max_chars(tmp_path):
    """to_prompt_block should truncate output to fit max_chars."""
    # Create many files to exceed max_chars easily
    for i in range(50):
        (tmp_path / f"long_filename_to_consume_space_{i}.py").write_text("x", encoding="utf-8")

    index = CodebaseIndex(tmp_path, max_files=100).build()
    block = index.to_prompt_block(max_chars=200)

    # 200 chars is very small, it should definitely truncate
    assert len(block) <= 200 + 100  # Allow some slack for the truncation message itself
    assert "truncated" in block


def test_respects_gitignore(tmp_path):
    """Indexer should respect simple patterns in .gitignore."""
    (tmp_path / ".gitignore").write_text("ignored_file.txt\nsecrets/\n", encoding="utf-8")
    (tmp_path / "ignored_file.txt").write_text("secret", encoding="utf-8")
    (tmp_path / "visible_file.txt").write_text("hello", encoding="utf-8")
    
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "key.txt").write_text("123", encoding="utf-8")

    index = CodebaseIndex(tmp_path).build()
    
    paths = [t["path"] for t in index._tree]
    assert "visible_file.txt" in paths
    assert "ignored_file.txt" not in paths
    assert "secrets" not in paths
    assert "secrets/key.txt" not in paths
