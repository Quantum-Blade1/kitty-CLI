from rich.console import Console
from rich.table import Table
from rich import box
from kittycode.memory.graph import KnowledgeGraph, NodeType

NODE_COLORS = {
    NodeType.PREFERENCE: "magenta",
    NodeType.FILE:       "cyan",
    NodeType.BUG:        "red",
    NodeType.FEATURE:    "green",
    NodeType.CONCEPT:    "blue",
    NodeType.PERSON:     "yellow",
    NodeType.FACT:       "white",
}

def render_graph_table(graph: KnowledgeGraph, console: Console,
                       max_nodes: int = 30):
    """
    Render the knowledge graph as a Rich table in the terminal.
    Shows: id, type (coloured), label, weight bar, edge count, last access.
    """
    table = Table(
        title="Memory Knowledge Graph",
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold magenta",
    )
    table.add_column("ID",       style="dim", width=10)
    table.add_column("Type",     width=12)
    table.add_column("Label",    width=28)
    table.add_column("Weight",   width=14)
    table.add_column("Edges",    width=7)
    table.add_column("Accessed", width=12)

    import time
    now = time.time()
    nodes = sorted(graph.nodes.values(), key=lambda n: n.weight, reverse=True)

    for node in nodes[:max_nodes]:
        color = NODE_COLORS.get(node.node_type, "white")
        bar_len = int(node.weight * 10)
        # Use ASCII fallbacks for Windows compatibility
        bar = "[green]" + "#" * bar_len + "[/green]" + "-" * (10 - bar_len)
        edge_count = len([e for e in graph.edges
                         if e.source == node.id or e.target == node.id])
        hours_ago = (now - node.last_accessed) / 3600
        if hours_ago < 48:
            accessed = f"{hours_ago:.1f}h ago"
        else:
            accessed = f"{hours_ago/24:.0f}d ago"

        table.add_row(
            node.id,
            f"[{color}]{node.node_type.value}[/{color}]",
            node.label[:26],
            bar + f" {node.weight:.2f}",
            str(edge_count),
            accessed,
        )

    console.print(table)
    console.print(f"[dim]{len(graph.nodes)} nodes | {len(graph.edges)} edges[/dim]")

def render_node_detail(graph: KnowledgeGraph, node_id: str, console: Console):
    """
    Show a single node and all its connections in detail.
    Called by: kitty memory --node <id>
    """
    node = graph.nodes.get(node_id)
    if not node:
        console.print(f"[red]Node '{node_id}' not found.[/red]")
        return

    color = NODE_COLORS.get(node.node_type, "white")
    console.print(f"\n[bold {color}]{node.label}[/bold {color}]  "
                  f"[dim]{node.node_type.value} · id={node.id}[/dim]")
    console.print(f"  Weight: {node.weight:.3f}  "
                  f"Accessed: {node.access_count}x")

    edges = [e for e in graph.edges
             if e.source == node_id or e.target == node_id]
    if edges:
        console.print("\n  [bold]Connections:[/bold]")
        for e in edges:
            other_id = e.target if e.source == node_id else e.source
            other = graph.nodes.get(other_id)
            if other:
                direction = "-->" if e.source == node_id else "<--"
                console.print(f"    {direction} [{e.edge_type.value}] "
                              f"[cyan]{other.label}[/cyan]  "
                              f"(strength={e.strength:.2f})")
