import uuid
import time
import math
from dataclasses import dataclass, field
from enum import Enum

class NodeType(str, Enum):
    PREFERENCE = "preference"   # user likes/dislikes
    FILE       = "file"         # source file or path
    BUG        = "bug"          # known issue
    FEATURE    = "feature"      # capability being built
    CONCEPT    = "concept"      # abstract idea
    PERSON     = "person"       # user or collaborator
    FACT       = "fact"         # general fact (default)

class EdgeType(str, Enum):
    RELATES_TO  = "relates_to"
    HAS_BUG     = "has_bug"
    DEPENDS_ON  = "depends_on"
    USES        = "uses"
    MENTIONED_IN = "mentioned_in"
    CAUSED_BY   = "caused_by"
    FIXED_BY    = "fixed_by"

@dataclass
class GraphNode:
    id: str
    label: str
    node_type: NodeType
    weight: float = 1.0          # importance, 0.0–1.0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    metadata: dict = field(default_factory=dict)

@dataclass
class GraphEdge:
    source: str      # node id
    target: str      # node id
    edge_type: EdgeType
    strength: float = 1.0   # 0.0–1.0, decays separately
    created_at: float = field(default_factory=time.time)

class KnowledgeGraph:

    def __init__(self):
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        self._adj: dict[str, list[str]] = {}   # id -> [neighbour ids]

    def add_node(self, label: str, node_type: NodeType = NodeType.FACT,
                 weight: float = 1.0, metadata: dict = None,
                 node_id: str = None) -> str:
        """Add a node. Returns node id. Deduplicates by label+type."""
        existing = self._find_by_label(label, node_type)
        if existing:
            existing.access_count += 1
            existing.last_accessed = time.time()
            return existing.id
        
        if not node_id:
            node_id = str(uuid.uuid4())[:8]
        
        self.nodes[node_id] = GraphNode(
            id=node_id, label=label, node_type=node_type,
            weight=weight, metadata=metadata or {}
        )
        self._adj[node_id] = []
        return node_id

    def add_edge(self, source_id: str, target_id: str,
                 edge_type: EdgeType = EdgeType.RELATES_TO,
                 strength: float = 1.0) -> bool:
        """Add a directed edge. Returns False if either node missing."""
        if source_id not in self.nodes or target_id not in self.nodes:
            return False
        # Deduplicate
        for e in self.edges:
            if e.source == source_id and e.target == target_id and e.edge_type == edge_type:
                e.strength = min(1.0, e.strength + 0.1)  # reinforce
                return True
        self.edges.append(GraphEdge(source_id, target_id, edge_type, strength))
        self._adj.setdefault(source_id, []).append(target_id)
        self._adj.setdefault(target_id, []).append(source_id)
        return True

    def spreading_activation(self, seed_ids: list[str],
                             decay: float = 0.5,
                             depth: int = 2,
                             top_k: int = 10) -> list[GraphNode]:
        """
        Spreading activation retrieval — the core of graphical memory.

        Algorithm:
        1. Initialise activation: seed nodes get activation = their weight.
        2. For each depth step, spread activation to neighbours:
               neighbour.activation += source.activation * edge.strength * decay
        3. Activation decays by `decay` factor per hop.
        4. Return top_k nodes sorted by final activation, excluding seeds.

        This models human associative memory — a strongly connected
        concept "lights up" nearby concepts through the graph.
        """
        activation: dict[str, float] = {}
        for sid in seed_ids:
            if sid in self.nodes:
                activation[sid] = self.nodes[sid].weight

        frontier = list(seed_ids)
        for _ in range(depth):
            next_frontier = []
            for node_id in frontier:
                node_act = activation.get(node_id, 0.0)
                # Find all edges connected to this node
                for edge in self.edges:
                    neighbour = None
                    if edge.source == node_id:
                        neighbour = edge.target
                    elif edge.target == node_id:
                        neighbour = edge.source
                    
                    if neighbour and neighbour in self.nodes:
                        spread = node_act * edge.strength * decay
                        activation[neighbour] = activation.get(neighbour, 0.0) + spread
                        next_frontier.append(neighbour)
            frontier = list(set(next_frontier))

        # Exclude seeds, sort by activation, return top_k
        results = [
            (act, self.nodes[nid])
            for nid, act in activation.items()
            if nid not in seed_ids and nid in self.nodes
        ]
        results.sort(key=lambda x: x[0], reverse=True)
        return [node for _, node in results[:top_k]]

    def _find_by_label(self, label: str, node_type: NodeType) -> GraphNode | None:
        for node in self.nodes.values():
            if node.label == label and node.node_type == node_type:
                return node
        return None

    def get_neighbours(self, node_id: str) -> list[GraphNode]:
        return [self.nodes[nid] for nid in self._adj.get(node_id, [])
                if nid in self.nodes]

    def to_dict(self) -> dict:
        return {
            "nodes": {k: {
                "id": v.id,
                "label": v.label,
                "node_type": v.node_type.value,
                "weight": v.weight,
                "created_at": v.created_at,
                "last_accessed": v.last_accessed,
                "access_count": v.access_count,
                "metadata": v.metadata
            } for k, v in self.nodes.items()},
            "edges": [{
                "source": e.source,
                "target": e.target,
                "edge_type": e.edge_type.value,
                "strength": e.strength,
                "created_at": e.created_at
            } for e in self.edges],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeGraph":
        g = cls()
        for k, v in data.get("nodes", {}).items():
            # Convert node_type string back to enum
            v["node_type"] = NodeType(v["node_type"])
            node = GraphNode(**v)
            g.nodes[k] = node
            g._adj[k] = []
        for ev in data.get("edges", []):
            # Convert edge_type string back to enum
            ev["edge_type"] = EdgeType(ev["edge_type"])
            edge = GraphEdge(**ev)
            g.edges.append(edge)
            g._adj.setdefault(edge.source, []).append(edge.target)
            g._adj.setdefault(edge.target, []).append(edge.source)
        return g
