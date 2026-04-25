"""
Quantum-inspired model routing for KittyCode.

Implements three quantum principles in pure Python:

1. SUPERPOSITION — each model candidate is represented as a quantum state
   with a complex amplitude. The amplitude encodes both magnitude (health score)
   and phase (task-fit angle).

2. INTERFERENCE — recent success/failure on the SAME task type constructively
   or destructively interferes with the model's amplitude.

3. AMPLITUDE AMPLIFICATION — a Grover-inspired iteration boosts the amplitude
   of the highest-scoring candidate relative to the others.

The final "measurement" (model selection) samples from |amplitude|^2 as a
probability distribution — the quantum Born rule.
"""

import math
import random
import time
from typing import List, Dict


TASK_PHASE = {
    "Code":    0.0,        # 0 rad
    "Chat":    math.pi / 4,  # 45 deg
    "Thought": math.pi / 2,  # 90 deg
}


def _build_amplitudes(
    model_keys: List[str],
    health,                 # ModelHealthTracker instance
    task_type: str,
    recent_log: List[Dict],
) -> Dict[str, complex]:
    """
    Step 1: Build initial superposition.

    Each model gets a complex amplitude:
        amplitude = health_score * e^(i * phase)
    where phase encodes how well the model fits this task type.
    """
    phase = TASK_PHASE.get(task_type, 0.0)
    amplitudes = {}
    for key in model_keys:
        score = health.get_health_score(key)  # 0..1
        # complex amplitude: magnitude = score, angle = task phase
        amplitudes[key] = score * complex(math.cos(phase), math.sin(phase))
    return amplitudes


def _apply_interference(
    amplitudes: Dict[str, complex],
    recent_log: List[Dict],
    task_type: str,
    window: int = 10,
) -> Dict[str, complex]:
    """
    Step 2: Apply interference from recent routing history.

    SUCCESS on this task_type -> constructive (multiply by e^(+i*delta))
    FAILURE on this task_type -> destructive   (multiply by e^(-i*delta))

    This shifts the phase, which changes |amplitude|^2 after normalisation.
    """
    delta = math.pi / 8   # interference strength (22.5 deg per event)
    relevant = [e for e in recent_log[-window:] if e.get("task") == task_type]
    for entry in relevant:
        model = entry.get("chosen", "")
        if model not in amplitudes:
            continue
        reason = entry.get("reason", "")
        if "SUCCESS" in reason:
            amplitudes[model] *= complex(math.cos(delta), math.sin(delta))
        elif "FAIL" in reason or "LOW_CONFIDENCE" in reason:
            amplitudes[model] *= complex(math.cos(-delta), math.sin(-delta))
    return amplitudes


def _amplitude_amplification(
    amplitudes: Dict[str, complex],
    iterations: int = 1,
) -> Dict[str, complex]:
    """
    Step 3: Grover-inspired amplitude amplification.

    One iteration: reflect around mean, then reflect around the marked state.
    The "marked" state is the one with the highest |amplitude|.
    This boosts the winner relative to the rest.
    """
    keys = list(amplitudes.keys())
    if len(keys) < 2:
        return amplitudes

    for _ in range(iterations):
        marked_key = max(keys, key=lambda k: abs(amplitudes[k]))
        # Phase flip for marked state
        amplitudes[marked_key] = -amplitudes[marked_key]
        
        amps = [amplitudes[k] for k in keys]
        mean_amp = sum(amps) / len(amps)
        # Inversion about mean: a_i -> 2*mean - a_i
        reflected = {k: 2 * mean_amp - amplitudes[k] for k in keys}
        amplitudes = reflected

    return amplitudes


def _measure(amplitudes: Dict[str, complex]) -> str:
    """
    Step 4: Quantum measurement.

    Probability of measuring model k = |amplitude_k|^2  (Born rule).
    Returns the sampled model key.
    """
    keys = list(amplitudes.keys())
    probs = [abs(amplitudes[k]) ** 2 for k in keys]
    total = sum(probs)
    if total == 0:
        return random.choice(keys)
    norm = [p / total for p in probs]
    # Weighted random sample
    r = random.random()
    cumulative = 0.0
    for key, prob in zip(keys, norm):
        cumulative += prob
        if r <= cumulative:
            return key
    return keys[-1]


def quantum_select(
    model_keys: List[str],
    health,
    task_type: str,
    recent_log: List[Dict],
    amplify_iterations: int = 1,
) -> List[str]:
    """
    Full quantum-inspired selection pipeline.

    Returns an ORDERED list of model keys, most-likely first.
    The router should try them in this order.
    """
    if not model_keys:
        return []
    if len(model_keys) == 1:
        return model_keys

    amps = _build_amplitudes(model_keys, health, task_type, recent_log)
    amps = _apply_interference(amps, recent_log, task_type)
    amps = _amplitude_amplification(amps, amplify_iterations)

    # Build ordered list by sampling WITHOUT replacement
    ordered = []
    remaining = dict(amps)
    for _ in range(len(model_keys)):
        if not remaining:
            break
        chosen = _measure(remaining)
        ordered.append(chosen)
        del remaining[chosen]

    return ordered
