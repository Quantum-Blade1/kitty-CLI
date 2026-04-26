import time
import pytest
from kittycode.memory.graph import KnowledgeGraph, NodeType, EdgeType
from kittycode.memory.decay import DecayEngine

def test_add_node_deduplicates():
    g = KnowledgeGraph()
    id1 = g.add_node("Python", NodeType.CONCEPT)
    id2 = g.add_node("Python", NodeType.CONCEPT)
    
    assert id1 == id2
    assert len(g.nodes) == 1
    assert g.nodes[id1].access_count == 1  # First access was 0, second access incremented to 1

def test_add_edge_creates_connection():
    g = KnowledgeGraph()
    id_a = g.add_node("Kitty", NodeType.PERSON)
    id_b = g.add_node("CLI", NodeType.CONCEPT)
    
    ok = g.add_edge(id_a, id_b, EdgeType.USES)
    assert ok is True
    assert len(g.edges) == 1
    assert g.edges[0].source == id_a
    assert g.edges[0].target == id_b

def test_spreading_activation_finds_neighbours():
    g = KnowledgeGraph()
    # A --uses--> B --has_bug--> C
    id_a = g.add_node("A", NodeType.FACT)
    id_b = g.add_node("B", NodeType.FACT)
    id_c = g.add_node("C", NodeType.FACT)
    
    g.add_edge(id_a, id_b, EdgeType.USES)
    g.add_edge(id_b, id_c, EdgeType.HAS_BUG)
    
    # Seed with A
    activated = g.spreading_activation([id_a], depth=2, top_k=10)
    
    # B and C should be in activated
    labels = [n.label for n in activated]
    assert "B" in labels
    assert "C" in labels
    assert "A" not in labels

def test_decay_reduces_weight():
    g = KnowledgeGraph()
    id_a = g.add_node("TempFact", NodeType.FACT)
    node = g.nodes[id_a]
    node.weight = 1.0
    
    # Manually set last_accessed to 48 hours ago
    node.last_accessed = time.time() - (48 * 3600)
    
    decay = DecayEngine()
    changed = decay.apply_decay(g)
    
    assert changed == 1
    assert node.weight < 1.0

def test_no_decay_for_preference():
    g = KnowledgeGraph()
    id_a = g.add_node("Dark Mode", NodeType.PREFERENCE)
    node = g.nodes[id_a]
    node.weight = 1.0
    
    # Manually set last_accessed to 48 hours ago
    node.last_accessed = time.time() - (48 * 3600)
    
    decay = DecayEngine()
    changed = decay.apply_decay(g)
    
    assert changed == 0
    assert node.weight == 1.0

def test_reinforce_increases_weight():
    g = KnowledgeGraph()
    id_a = g.add_node("Fact", NodeType.FACT)
    node = g.nodes[id_a]
    node.weight = 0.5
    
    decay = DecayEngine()
    decay.reinforce(node)
    
    assert node.weight > 0.5
    assert node.weight <= 1.0

def test_graph_serialise_roundtrip():
    g = KnowledgeGraph()
    id_a = g.add_node("A", NodeType.FACT)
    id_b = g.add_node("B", NodeType.BUG)
    id_c = g.add_node("C", NodeType.FEATURE)
    
    g.add_edge(id_a, id_b, EdgeType.RELATES_TO)
    g.add_edge(id_b, id_c, EdgeType.CAUSED_BY)
    
    data = g.to_dict()
    g2 = KnowledgeGraph.from_dict(data)
    
    assert len(g2.nodes) == 3
    assert len(g2.edges) == 2
    assert "A" in [n.label for n in g2.nodes.values()]
    assert EdgeType.RELATES_TO in [e.edge_type for e in g2.edges]
