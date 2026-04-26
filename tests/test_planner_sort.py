"""Tests for Planner topological sorting"""

import pytest
from kittycode.agent.planner import _extract_file_deps, _topo_sort

def test_topo_sort_basic():
    steps = [
        {"step": "Write utils", "writes": ["utils.py"], "reads": []},
        {"step": "Write main", "writes": ["main.py"], "reads": ["utils.py"]},
        {"step": "Run tests", "writes": [], "reads": ["main.py"]}
    ]
    
    # Intentionally shuffle
    shuffled = [steps[2], steps[0], steps[1]]
    
    deps = _extract_file_deps(shuffled)
    sorted_steps = _topo_sort(shuffled, deps)
    
    # Expected order: utils -> main -> tests
    assert sorted_steps[0]["writes"] == ["utils.py"]
    assert sorted_steps[1]["writes"] == ["main.py"]
    assert "tests" in sorted_steps[2]["step"].lower()

def test_topo_sort_test_dependency():
    steps = [
        {"step": "Run tests", "writes": [], "reads": []},
        {"step": "Write feature", "writes": ["feature.py"], "reads": []},
    ]
    
    deps = _extract_file_deps(steps)
    sorted_steps = _topo_sort(steps, deps)
    
    # Test should come last even if no explicit reads
    assert sorted_steps[0]["writes"] == ["feature.py"]
    assert "tests" in sorted_steps[1]["step"].lower()
