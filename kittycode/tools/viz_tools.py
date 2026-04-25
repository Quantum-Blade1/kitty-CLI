from rich.tree import Tree
from rich.table import Table
from rich.panel import Panel
from rich.console import Console, Group
from typing import Dict, List, Any

def draw_tree(label: str, children: Dict[str, Any]) -> str:
    """
    Renders a hierarchical tree structure in the terminal.
    'children' should be a nested dictionary of strings/dicts.
    """
    tree = Tree(f"[kruby]{label}[/kruby]")
    
    def add_nodes(parent_tree, data):
        if isinstance(data, dict):
            for key, value in data.items():
                node = parent_tree.add(f"[ktext]{key}[/ktext]")
                add_nodes(node, value)
        elif isinstance(data, list):
            for item in data:
                parent_tree.add(f"[kmuted]{item}[/kmuted]")
        else:
            parent_tree.add(f"[kmuted]{data}[/kmuted]")
            
    add_nodes(tree, children)
    
    # We return the renderable but also print it for immediate feedback
    from kittycode.cli.ui import console
    console.print("\n", tree, "\n")
    return f"Rendered tree: {label}"

def draw_table(title: str, headers: List[str], rows: List[List[Any]]) -> str:
    """
    Renders a beautiful table for data comparison.
    """
    table = Table(title=f"[kruby]{title}[/kruby]", border_style="kborder", expand=False)
    for h in headers:
        table.add_column(h, style="ktext")
    
    for r in rows:
        table.add_row(*[str(item) for item in r])
        
    from kittycode.cli.ui import console
    console.print("\n", table, "\n")
    return f"Rendered table: {title}"

def draw_chart(title: str, data: Dict[str, float]) -> str:
    """
    Renders a simple ASCII bar chart using unicode characters.
    """
    if not data:
        return "No data to chart."
        
    max_val = max(data.values())
    chart_width = 30
    
    table = Table(title=f"[kruby]{title}[/kruby]", border_style="kborder", show_header=False, expand=False)
    
    for key, val in data.items():
        bar_len = int((val / max_val) * chart_width) if max_val > 0 else 0
        bar = "█" * bar_len + "░" * (chart_width - bar_len)
        table.add_row(f"[ktext]{key}[/ktext]", f"[kruby]{bar}[/kruby] [kmuted]{val}[/kmuted]")
        
    from kittycode.cli.ui import console
    console.print("\n", table, "\n")
    return f"Rendered chart: {title}"

def setup_viz_tools(registry):
    """Registers visualization tools into the provided registry."""
    registry.register(
        name="draw_tree",
        description="Renders a hierarchical tree diagram. Use for file structures, organization, or logic flows.",
        parameters={
            "label": "String. Root label of the tree.",
            "children": "Object. Nested dictionary/list structure to render."
        },
        func=draw_tree,
        destructive=False
    )
    
    registry.register(
        name="draw_table",
        description="Renders a data table. Use for comparisons, feature lists, or structured data.",
        parameters={
            "title": "String. Table title.",
            "headers": "Array of strings. Column headers.",
            "rows": "Array of arrays. Each inner array is a row of data."
        },
        func=draw_table,
        destructive=False
    )
    
    registry.register(
        name="draw_chart",
        description="Renders a bar chart. Use for metrics, performance, or numerical comparisons.",
        parameters={
            "title": "String. Chart title.",
            "data": "Object. Mapping of labels to numeric values."
        },
        func=draw_chart,
        destructive=False
    )
