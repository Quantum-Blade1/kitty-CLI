"""
Quantum-inspired task ordering for KittyCode planner.

Applies quantum annealing principles to reorder the step queue:

PROBLEM: Given N steps in a plan, what ordering minimises the risk of
a later step breaking the output of an earlier step?

QUANTUM PRINCIPLE: Quantum tunnelling allows the system to pass through
energy barriers. We model this as a temperature-decaying tunnelling
probability that lets suboptimal orderings be accepted early (exploration)
and rejected late (exploitation). This is Simulated Annealing with a
quantum tunnelling schedule (Cauchy distribution) instead of the classical
Boltzmann acceptance criterion.
"""

import math
import random
from typing import List, Dict


def _cost(step: Dict) -> float:
    """
    Cost of a step based on its properties.
    Executable steps (file writes, commands) have higher cost if placed first
    without a preceding reasoning step. We penalise out-of-order execution.
    """
    is_exec = step.get("executable", False)
    return 1.0 if is_exec else 0.3


def _sequence_cost(steps: List[Dict]) -> float:
    """
    Total cost of a step sequence.
    Penalises executable steps that appear before any reasoning step.
    Also penalises two consecutive executable steps (no analysis between them).
    """
    total = 0.0
    has_reasoning = False
    for i, step in enumerate(steps):
        is_exec = step.get("executable", False)
        if not is_exec:
            has_reasoning = True
        if is_exec and not has_reasoning:
            total += 2.0   # heavy penalty: exec before any analysis
        if i > 0 and is_exec and steps[i-1].get("executable", False):
            total += 1.0   # consecutive exec steps — no reasoning between
        total += _cost(step)
    return total


def _tunnelling_prob(delta_cost: float, temperature: float) -> float:
    """
    Quantum tunnelling acceptance probability.
    Uses Cauchy distribution (heavier tails than Boltzmann/Gaussian)
    which models quantum tunnelling through energy barriers more accurately.
    P(accept worse) = 1 / (1 + (delta_cost/temperature)^2)
    """
    if temperature < 1e-10:
        return 0.0
    ratio = delta_cost / temperature
    return 1.0 / (1.0 + ratio * ratio)


def quantum_anneal_steps(
    steps: List[Dict],
    initial_temp: float = 2.0,
    cooling_rate: float = 0.85,
    iterations: int = 200,
) -> List[Dict]:
    """
    Reorder a list of plan steps using quantum annealing.
    Returns the reordered list. Reasoning steps will be pulled before
    the executable steps they set up.

    Args:
        steps: plan queue from Planner.generate_plan()
        initial_temp: starting tunnelling temperature (higher = more exploration)
        cooling_rate: geometric decay per iteration (0 < rate < 1)
        iterations: number of annealing steps
    """
    if len(steps) <= 2:
        return steps   # too small to optimise

    current = list(steps)
    current_cost = _sequence_cost(current)
    best = list(current)
    best_cost = current_cost
    temperature = initial_temp

    for _ in range(iterations):
        # Propose a swap of two random adjacent steps
        i = random.randint(0, len(current) - 2)
        candidate = list(current)
        candidate[i], candidate[i + 1] = candidate[i + 1], candidate[i]

        candidate_cost = _sequence_cost(candidate)
        delta = candidate_cost - current_cost

        if delta < 0:
            # Candidate is better — always accept
            current = candidate
            current_cost = candidate_cost
        else:
            # Candidate is worse — accept with quantum tunnelling probability
            if random.random() < _tunnelling_prob(delta, temperature):
                current = candidate
                current_cost = candidate_cost

        if current_cost < best_cost:
            best = list(current)
            best_cost = current_cost

        temperature *= cooling_rate

    return best
