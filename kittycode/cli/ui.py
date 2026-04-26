from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
from rich.console import Console, Group
from rich.markdown import Markdown
from kittycode.config.settings import MAX_WIDTH

# --- Themes Dictionary ---
THEMES = {
    "catgirl": {
        "kruby": "bold #E91E63",        # Ruby Pinkish-Red (Kitty's soul)
        "kred": "bold #FF5252",         # Bright Ruby Red
        "ksurface": "#130D0E",          # Near-black Wine
        "kmuted": "#757575",            # Muted Gray
        "ktext": "#F5F5F5",             # Off-White
        "kwhite": "bold #FFFFFF",       # Pure White
        "kborder": "#3D1B21",           # Deep Wine Border
        "kgreen": "bold #39FF14",       # Code Green
        "kbg": "on #130D0E"             # Background fill
    },
    "ps1": {
        "kruby": "bold #00FFFF",        # Neon Cyan
        "kred": "bold #FFFF00",         # Vibrant Yellow
        "ksurface": "#000000",          # Pure Black
        "kmuted": "#808080",            # Scanline Gray
        "ktext": "#C0C0C0",             # PS1 BIOS Gray
        "kwhite": "bold #FFFFFF",       # Pure White
        "kborder": "#0000FF",           # Memory Card Blue
        "kgreen": "bold #39FF14",       # Code Green
        "kbg": "on #000000"             # Pure Black fill
    },
    "cyberpunk": {
        "kruby": "bold #FCEE0A",        # Night City Yellow
        "kred": "bold #FF003C",         # Arasaka Red
        "ksurface": "#0A0A0A",          # Asphalt Black
        "kmuted": "#505050",            # Chrome Gray
        "ktext": "#00FFFF",             # Neon Cyan Text
        "kwhite": "bold #FFFFFF",       # Pure White
        "kborder": "#00FFFF",           # Neon Cyan Border
        "kgreen": "bold #39FF14",       # Code Green
        "kbg": "on #0A0A0A"             # Asphalt fill
    },
    "matrix": {
        "kruby": "bold #00FF41",        # Matrix Green
        "kred": "bold #008F11",         # Darker Matrix Green
        "ksurface": "#000000",          # Pure Black
        "kmuted": "#003B00",            # Faded Green
        "ktext": "#00FF41",             # Hacker Green Text
        "kwhite": "bold #FFFFFF",       # Pure White
        "kborder": "#008F11",           # Dark Green Border
        "kgreen": "bold #39FF14",       # Code Green
        "kbg": "on #000000"             # Pure Black fill
    },
    "dracula": {
        "kruby": "bold #FF79C6",        # Dracula Pink
        "kred": "bold #FF5555",         # Dracula Red
        "ksurface": "#282A36",          # Dracula Background
        "kmuted": "#6272A4",            # Dracula Comment
        "ktext": "#F8F8F2",             # Dracula Foreground
        "kwhite": "bold #FFFFFF",       # Pure White
        "kborder": "#BD93F9",           # Dracula Purple
        "kgreen": "bold #50FA7B",       # Code Green
        "kbg": "on #282A36"             # Dracula fill
    }
}

kitty_theme = Theme(THEMES["catgirl"])

console = Console(theme=kitty_theme)

def setup_theme(theme_name: str):
    if theme_name in THEMES:
        console.push_theme(Theme(THEMES[theme_name]))

def get_header(current_mode):
    logo_art = r"""
    /\_/\  
   ( o.o ) 
    > ^ <
    """


    grid = Table.grid(expand=False, padding=(0, 2))
    grid.add_column(justify="left")
    grid.add_column(justify="left")
    
    logo = Text(logo_art, style="kruby")
    
    modes = ["Chat", "Code", "About", "Stats"]
    pills = []
    for m in modes:
        if m == current_mode:
            pills.append(f"[kwhite on kruby] {m} [/kwhite on kruby]")
        else:
            pills.append(f"[kmuted]{m}[/kmuted]")
    
    header_info = Group(
        Text("^^ KITTYCODE v2.0", style="kruby bold"),
        Text.from_markup("   ".join(pills))
    )
    
    grid.add_row(logo, header_info)
    return Panel(grid, border_style="kborder", padding=(0, 1), expand=False)


def get_footer(mem_count, current_mode, user_name, project_root):
    grid = Table.grid(expand=False, padding=(0, 4))
    grid.add_column(justify="left")
    grid.add_column(justify="left")
    
    status = Text.from_markup(f"[kruby]Link: {mem_count}[/kruby] | [kwhite]{current_mode}[/kwhite] | [ktext]{user_name}[/ktext] | [kmuted]{project_root}[/kmuted]")
    hints = Text.from_markup("[kmuted]Hints: 'shift' (mode) | 'stats' | 'setup'[/kmuted]")
    
    grid.add_row(status, hints)
    return grid


def render_bubble(role, content, user_name="User", logs=None):
    if role == "kitty":
        renderables = [Markdown(content)]
        if logs:
            log_text = Text("\n── Work Log", style="kmuted")
            for r in logs: 
                log_text.append(f"\n  • ", style="kruby")
                log_text.append(f"{r}", style="kmuted italic")
            renderables.append(log_text)
        
        return Panel(
            Group(*renderables), 
            title="[kruby] K [/kruby]", 
            title_align="left", 
            style="kbg", 
            border_style="kborder", 
            width=MAX_WIDTH, 
            padding=(0, 1), 
            expand=False
        )
    else:
        display_content = content.ljust(15) if len(content) < 15 else content
        return Panel(
            Text(display_content, style="ktext"), 
            border_style="kruby", 
            padding=(0, 1), 
            subtitle=f"[kruby] {user_name} [/kruby]", 
            subtitle_align="right", 
            expand=False
        )


