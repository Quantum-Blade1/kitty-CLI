import typer
from rich.console import Console, Group
from rich.panel import Panel
from rich.theme import Theme
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.live import Live
from rich.rule import Rule
from kitty_agent import KittyAgent
import time
import os

# --- Ruby Noir Theme (Red, White, & Wine) ---
kitty_theme = Theme({
    "kruby": "bold #E91E63",        # Ruby Pinkish-Red (Kitty's soul)
    "kred": "bold #FF5252",         # Bright Ruby Red
    "ksurface": "#130D0E",          # Near-black Wine
    "kmuted": "#757575",            # Muted Gray
    "ktext": "#F5F5F5",             # Off-White
    "kwhite": "bold #FFFFFF",       # Pure White
    "kborder": "#3D1B21",           # Deep Wine Border
    "kgreen": "bold #39FF14"        # Code Green ( Dayton style )
})

console = Console(theme=kitty_theme)
app = typer.Typer()
kitty = KittyAgent()

# --- Responsive Config ---
MAX_WIDTH = 85 

# --- Global State ---
class AppState:
    current_mode = "Chat" 
    histories = {"Chat": [], "Code": [], "About": []}
    current_thought = "Kitty is waking up... nya~ ♥"
    user_name = "User"
    running = True

state = AppState()

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_header():
    grid = Table.grid(expand=False, padding=(0, 4))
    grid.add_column(justify="left")
    grid.add_column(justify="left")
    logo = Text("ฅ^•ﻌ•^ฅ KittyCode", style="kruby")
    modes = ["Chat", "Code", "About"]
    pills = [f"[kred]▶ {m}[/kred]" if m == state.current_mode else f"[kmuted]{m}[/kmuted]" for m in modes]
    grid.add_row(logo, Text.from_markup("   ".join(pills)))
    return Panel(grid, border_style="kborder", padding=(0, 1), expand=False)

def get_footer():
    mem_count = len(kitty.memory.get("facts", {}))
    grid = Table.grid(expand=False, padding=(0, 4))
    grid.add_column(justify="left")
    grid.add_column(justify="left")
    status = Text.from_markup(f"[kmuted]Link: {mem_count} | Mode: {state.current_mode} | User: {state.user_name}[/kmuted]")
    hints = Text.from_markup("[kmuted]Type 'shift' or mode name to switch[/kmuted]")
    grid.add_row(status, hints)
    return grid

def render_bubble(role, content, logs=None):
    if role == "kitty":
        renderables = [Markdown(content)]
        if logs:
            log_text = Text("\nฅ^•ﻌ•^ฅ Work Log:", style="kruby")
            for r in logs: log_text.append(f"\n • {r}", style="ktext")
            renderables.append(log_text)
        return Panel(Group(*renderables), title="[kruby]ฅ[/kruby]", title_align="left", style="on #130D0E", border_style="kborder", width=MAX_WIDTH, padding=(0, 1), expand=False)
    else:
        display_content = content.ljust(15) if len(content) < 15 else content
        return Panel(Text(display_content, style="ktext"), border_style="kruby", padding=(0, 1), subtitle=Text(state.user_name, style="kruby"), subtitle_align="right", expand=False)

def typewriter_stream(text, logs=None):
    displayed = ""
    with Live(auto_refresh=True, console=console) as live:
        for char in text:
            displayed += char
            live.update(Panel(Text(displayed, style="ktext"), title="[kruby]ฅ[/kruby]", title_align="left", style="on #130D0E", border_style="kborder", width=MAX_WIDTH, padding=(0, 1), expand=False))
            time.sleep(0.005)
        live.update(render_bubble("kitty", text, logs=logs))

# --- Protocol Shifting Engine ---
# KittyCode uses a state-based protocol engine to switch between different
# operational modes (Chat, Code, About) while maintaining persistent context.
def show_mode_menu():
    clear(); console.print(get_header()); console.print("\n[kruby]ฅ^•ﻌ•^ฅ Protocol Shift[/kruby]")
    menu = Table.grid(padding=(0, 4))
    menu.add_column(style="kruby", justify="right"); menu.add_column(style="ktext")
    menu.add_row("1.", "Chat Mode"); menu.add_row("2.", "Code Mode"); menu.add_row("3.", "About"); menu.add_row("0.", "Cancel")
    console.print(Panel(menu, border_style="kborder", expand=False, padding=(1, 2)))
    choice = Prompt.ask("\n[kruby]Select Mode[/kruby]", choices=["1", "2", "3", "0"])
    mapping = {"1": "Chat", "2": "Code", "3": "About"}
    if choice != "0": state.current_mode = mapping[choice]; return True
    return False

# --- Intelligence Layer: Dynamic Greetings ---
# Kitty periodically refreshes her thoughts via GPT-4o, ensuring that 
# every mode transition and screen refresh carries a unique, warm message.
def refresh_thought():
    with console.status("[kruby]Kitty is thinking of you...[/kruby]", spinner="dots"):
        state.current_thought = str(kitty.get_thought()).strip()

def show_screen():
    clear(); console.print(get_header()); console.print("\n", end="")
    if state.current_mode == "About":
        msg = f"# ♥ The Story of KittyCode ♥\nI built this kitty with everything I know. This is a special world created by **Krish** just for **{state.user_name}**. I create my kitty and wt my kitty can do yes! lets go. **Me & Kitty are always in your corner! ฅ^•ﻌ•^ฅ**"
        console.print(Panel(Markdown(msg), border_style="kruby", width=MAX_WIDTH, expand=False))
        Prompt.ask("\n[kmuted]Press Enter to return to protocols...[/kmuted]")
        state.current_mode = "Chat"; return
    history = state.histories[state.current_mode]
    if not history:
        console.print(Text("ฅ^•ﻌ•^ฅ", style="kruby"))
        console.print(Text(state.current_thought, style="italic ktext"), "\n")
        chips = ["Help me", "Shift", "About"] if state.current_mode == "Chat" else ["New File", "LS", "Shift"]
        grid = Table.grid(expand=False, padding=(0, 2))
        grid.add_row(*[Panel(f"[kmuted]{c}[/kmuted]", border_style="kborder", expand=False) for c in chips])
        console.print(grid)
    else:
        for role, msg, *extra in history:
            logs = extra[0] if extra else None
            console.print(render_bubble(role, msg, logs=logs))
    console.print("\n", get_footer())

# --- Onboarding Protocol ---
# Kitty identifies first-time users by checking her persistent memory.
# If unknown, she performs a warm introduction and registers their name permanently.
def onboarding():
    clear()
    console.print(Align.center(Text("\nฅ^•ﻌ•^ฅ Welcome to KittyCode!", style="kruby")))
    console.print(Align.center(Text("I'm your new intelligent companion. I'd love to know your name!\n", style="ktext")))
    name = Prompt.ask("[kruby]What shall I call you?[/kruby]").strip()
    if not name: name = "Friend"
    kitty.memory["user_name"] = name
    kitty._save_memory()
    state.user_name = name
    console.print(Align.center(Text(f"\nNya~ It's wonderful to meet you, {name}! ♥", style="kred")))
    time.sleep(1.5)

@app.callback(invoke_without_command=True)
def main_loop(ctx: typer.Context):
    if ctx.invoked_subcommand is not None: return
    if not kitty.memory.get("user_name"): onboarding()
    else: state.user_name = kitty.memory["user_name"]
    refresh_thought()
    while state.running:
        show_screen()
        try:
            user_input = console.input(f"\n[kruby]>[/kruby] [kmuted]talk to kitty({state.current_mode.lower()})...[/kmuted] ").strip()
        except EOFError: break
        if not user_input: continue
        low = user_input.lower()
        mode_map = {"chat": "Chat", "code": "Code", "about": "About"}
        if low in mode_map: state.current_mode = mode_map[low]; refresh_thought(); continue
        if low in ["shift", "/", "menu"]:
            if show_mode_menu(): refresh_thought()
            continue
        if low in ["exit", "quit", "0"]: console.print(f"\n[kruby]Goodbye, {state.user_name}! ♥[/kruby]"); time.sleep(1); state.running = False; continue
        state.histories[state.current_mode].append(("user", user_input))
        show_screen()
        with console.status("[kruby]ฅ•ﻌ•... thinking[/kruby]", spinner="dots"):
            ctx_str = f"MODE: {state.current_mode}. "
            resp, actions = kitty.get_response(ctx_str + user_input)
        typewriter_stream(resp, logs=actions)
        state.histories[state.current_mode].append(("kitty", resp, actions))

if __name__ == "__main__":
    app()
