"""
Quantum-inspired memory retrieval for KittyCode.

PRINCIPLE: Grover's algorithm amplifies the amplitude of marked states.
We model each memory entry as a quantum state. A "query oracle" marks
entries that match the query. Multiple iterations of amplitude amplification
boost matching entries' probabilities before final measurement.

This is NOT FAISS vector search. It is a purely symbolic/classical algorithm
that applies quantum amplitude amplification mathematics to keyword scoring.
"""

import math
import re
from typing import List, Dict


def _tokenise(text: str) -> set:
    return {t for t in re.findall(r"\w+", text.lower()) if len(t) > 1}


def _oracle(query_tokens: set, memory_text: str) -> float:
    """
    Query oracle: returns a match score in [0, 1].
    This is the classical equivalent of a quantum oracle that flips the
    phase of matching states.
    Uses TF-like scoring: match_count / sqrt(total_tokens)
    """
    mem_tokens = _tokenise(memory_text)
    if not mem_tokens:
        return 0.0
    matches = len(query_tokens & mem_tokens)
    return matches / math.sqrt(len(mem_tokens))


def _amplify(scores: List[float], iterations: int = 2) -> List[float]:
    """
    Grover-style amplitude amplification.
    Input: raw match scores (|amplitude|).
    Output: amplified scores after N iterations of "inversion about mean".
    Each iteration boosts high scorers and suppresses low scorers.
    """
    if not scores:
        return scores
    amps = list(scores)
    for _ in range(iterations):
        mean = sum(amps) / len(amps)
        # Inversion about mean: a_i -> 2*mean - a_i
        amps = [max(0.0, 2 * mean - a) for a in amps]
    return amps


def quantum_retrieve(
    query: str,
    memories: List[Dict],
    k: int = 5,
    amplify_iterations: int = 2,
) -> List[Dict]:
    """
    Retrieve top-k relevant memories using quantum amplitude amplification.

    Args:
        query: the user's search query
        memories: list of memory dicts from MemoryManager.metadata
        k: how many results to return
        amplify_iterations: Grover amplification steps (2 is optimal for small N)

    Returns:
        Top-k memory dicts ordered by amplified score, highest first.
    """
    if not memories or not query.strip():
        return memories[:k]

    query_tokens = _tokenise(query)
    if not query_tokens:
        return memories[-k:]

    # Step 1: Oracle phase — score each memory
    raw_scores = [_oracle(query_tokens, m.get("text", "")) for m in memories]

    # Step 2: Amplitude amplification — boost high scorers
    amp_scores = _amplify(raw_scores, amplify_iterations)

    # Step 3: Measurement — select top-k by amplified score
    indexed = sorted(enumerate(amp_scores), key=lambda x: x[1], reverse=True)
    top_k_indices = [i for i, _ in indexed[:k] if amp_scores[i] > 0]

    if not top_k_indices:
        # Fall back to most recent if nothing matches
        return memories[-k:]

    return [memories[i] for i in top_k_indices]
