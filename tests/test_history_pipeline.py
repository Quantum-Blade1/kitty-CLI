"""
Tests for the 5-stage history compaction pipeline.
"""

import pytest
from kittycode.memory.history import HistoryManager

class MockSummarizer:
    def summarize(self, messages):
        return "Summary of " + str(len(messages)) + " messages"

@pytest.fixture
def hm():
    mgr = HistoryManager()
    mgr.summarizer = MockSummarizer()
    return mgr

def test_stage1_removes_no_change_results(hm):
    history = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Run tests"},
        {"role": "assistant", "content": "Result"},
        {"role": "user", "content": "More tests"},
        {"role": "assistant", "content": "Result"},
        {"role": "user", "content": "Check status"},
        {"role": "assistant", "content": "Working tree clean"}, # Low value
        {"role": "user", "content": "Actual msg"},
        {"role": "assistant", "content": "Actual response"},
    ]
    trimmed = hm.trim(history)
    
    # Should remove "Working tree clean" but it's within the last 4 messages in this list
    # Wait, history length is 9. last 4 are index 5,6,7,8.
    # index 6 is "Working tree clean". So it should stay if it's within last 4.
    
    # Let's add more messages to push it out of last 4
    history.extend([
        {"role": "user", "content": "m1"},
        {"role": "assistant", "content": "r1"},
        {"role": "user", "content": "m2"},
        {"role": "assistant", "content": "r2"},
    ])
    # Now "Working tree clean" is far from end.
    trimmed = hm.trim(history)
    contents = [m["content"] for m in trimmed]
    assert "Working tree clean" not in contents

def test_stage2_snips_long_messages(hm):
    long_content = "X" * 3000
    history = [
        {"role": "system", "content": "S"},
        {"role": "user", "content": long_content}, # Middle message
        {"role": "assistant", "content": "A"},
        {"role": "user", "content": "U"},
        {"role": "assistant", "content": "A"},
        {"role": "user", "content": "U"},
        {"role": "assistant", "content": "A"},
        {"role": "user", "content": "U"},
        {"role": "assistant", "content": "A"},
        {"role": "user", "content": "U"},
        {"role": "assistant", "content": "A"},
    ]
    trimmed = hm.trim(history)
    snipped = trimmed[1]["content"]
    assert "snipped" in snipped
    assert len(snipped) < 2000

def test_stage3_microcompacts_at_threshold(hm):
    # Use many messages to exceed 12k even after stage 2 snipping
    msg = "A" * 4000
    history = [{"role": "system", "content": "S"}] + [{"role": "user", "content": msg} for _ in range(50)]
    
    trimmed = hm.trim(history)
    assert any("[MICROCOMPACT SUMMARY]" in m["content"] for m in trimmed)

def test_stage4_collapses_at_24k_tokens(hm):
    # Disable stage 3 to reach stage 4
    hm._stage_3_microcompact = lambda x: x
    
    msg = "A" * 4000
    # 100 messages to exceed 24k after snip
    history = [{"role": "system", "content": "S"}] + [{"role": "user", "content": msg} for _ in range(100)]
    
    trimmed = hm.trim(history)
    assert any("[CONTEXT COLLAPSED]" in m["content"] for m in trimmed)
    assert len(trimmed) == 4

def test_stage5_hard_ceiling(hm):
    # Disable stage 3 and 4 to reach stage 5
    hm._stage_3_microcompact = lambda x: x
    hm._stage_4_context_collapse = lambda x: x
    
    msg = "A" * 4000
    # 150 messages to exceed 32k after snip
    history = [{"role": "system", "content": "S"}] + [{"role": "user", "content": msg} for _ in range(150)]
    
    trimmed = hm.trim(history)
    assert len(trimmed) == 20



