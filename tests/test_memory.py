from kittycode.memory.manager import MemoryManager


def test_memory_retrieval_works_offline():
    m = MemoryManager(max_memories=10)

    m.set_fact("user_likes", "User really enjoys parsing logs.")
    m.set_fact("user_favorite_color", "The user's favorite color is pastel pink.")
    m.set_fact("project_goal", "The user wants to build a local AI sandbox.")
    m.set_fact("ai_rules", "Kitty must always be polite and say nya.")

    results = m.get_relevant_context("What does the user want to build?", k=3)
    joined = " ".join(results).lower()
    assert "build" in joined or "project_goal" in joined

    pink = m.get_relevant_context("pink", k=2)
    assert any("pink" in r.lower() for r in pink)
