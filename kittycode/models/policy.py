from typing import List

from kittycode.models.health import ModelHealthTracker


def build_routing_chain(base_list: List[str], health: ModelHealthTracker) -> List[str]:
    """
    Build adaptive routing order.
    Priority:
    1. Healthy models before demoted models.
    2. Preference order (primary first).
    3. Health score as tie-breaker.
    """
    healthy = [m for m in base_list if health.is_healthy(m)]
    if not healthy:
        health.reset_health()
        healthy = base_list[:]

    # lower index = higher configured priority
    healthy.sort(
        key=lambda m: (
            -base_list.index(m),
            health.get_health_score(m),
        ),
        reverse=True,
    )
    return healthy
