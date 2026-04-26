import math
import time

DECAY_RATE_PER_HOUR = 0.005    # weight loss per hour for normal facts
MIN_WEIGHT = 0.05              # floor — nothing fully disappears
NO_DECAY_TYPES = {"preference", "person"}  # identity-level nodes never decay

class DecayEngine:
    """
    Applies temporal decay to graph node weights.

    Decay formula (Ebbinghaus-inspired):
        new_weight = max(MIN_WEIGHT, weight * e^(-decay_rate * hours_elapsed))

    Nodes are reinforced (weight boosted toward 1.0) each time they
    are accessed — this models memory consolidation through repetition.
    """

    def apply_decay(self, graph) -> int:
        """
        Apply decay to all nodes in the graph.
        Returns the number of nodes whose weight changed.
        """
        now = time.time()
        changed = 0
        for node in graph.nodes.values():
            if node.node_type.value in NO_DECAY_TYPES:
                continue
            hours = (now - node.last_accessed) / 3600.0
            new_weight = max(
                MIN_WEIGHT,
                node.weight * math.exp(-DECAY_RATE_PER_HOUR * hours)
            )
            if abs(new_weight - node.weight) > 0.001:
                node.weight = round(new_weight, 4)
                changed += 1
        return changed

    def reinforce(self, node, boost: float = 0.15):
        """
        Reinforce a node on access — weight moves toward 1.0.
        Called automatically when a node is retrieved.
        """
        node.weight = min(1.0, node.weight + boost * (1.0 - node.weight))
        node.last_accessed = time.time()
        node.access_count += 1

    def prune_weak_nodes(self, graph, threshold: float = 0.05) -> list[str]:
        """
        Remove nodes whose weight has decayed below the threshold.
        Never removes nodes of type PREFERENCE or PERSON.
        Returns list of pruned node ids.
        """
        to_remove = [
            nid for nid, node in graph.nodes.items()
            if node.weight <= threshold
            and node.node_type.value not in NO_DECAY_TYPES
        ]
        for nid in to_remove:
            del graph.nodes[nid]
            graph._adj.pop(nid, None)
            # Remove all edges connected to this node
            graph.edges = [e for e in graph.edges
                           if e.source != nid and e.target != nid]
        return to_remove
