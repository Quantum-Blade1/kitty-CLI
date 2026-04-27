import json
import time
from contextlib import contextmanager
from functools import wraps
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Dict, List

import typer
from click import get_current_context
from rich.align import Align
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from kittycode.agent.kitty import KittyAgent
from kittycode.cli.ui import console, get_footer, get_header, render_bubble, setup_theme
from kittycode.config.settings import MAX_WIDTH, PROJECT_ROOT, RuntimeConfig
from kittycode.utils.helpers import clear

app = typer.Typer(
    help="KittyCode production CLI: interactive co-pilot with safe execution, memory, and model routing.",
    add_completion=True,
)
memory_app = typer.Typer(invoke_without_command=True, help="Structured memory operations.")
app.add_typer(memory_app, name="memory")
kitty = None  # Deferred init until needed

EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_USAGE_ERROR = 2

def get_memory_manager():
    from kittycode.memory.manager import MemoryManager

    return MemoryManager()



class AppState:
    current_mode = "Chat"
    histories = {"Chat": [], "Code": [], "About": []}
    current_thought = "Kitty is waking up..."
    user_name = "User"
    current_theme = "catgirl"
    running = True


state = AppState()


def ensure_kitty() -> KittyAgent:
    global kitty
    if kitty is None:
        kitty = KittyAgent()
    return kitty


def is_json_mode() -> bool:
    ctx = get_current_context(silent=True)
    if not ctx or not ctx.obj:
        return False
    return bool(ctx.obj.get("json", False))


def emit_json(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=True))


@contextmanager
def command_observer(command_name: str):
    from kittycode.telemetry.logger import get_logger, new_trace
    from kittycode.utils.stats import StatsManager

    trace_id = new_trace()
    log = get_logger("cli.command")
    started = time.time()
    ok = False
    log.info("command_start", trace_id=trace_id, command=command_name)
    try:
        yield
        ok = True
    except typer.Exit as e:
        ok = getattr(e, "exit_code", 1) == 0
        raise
    except Exception as e:
        log.error("command_exception", trace_id=trace_id, command=command_name, error=str(e)[:200])
        ok = False
        raise
    finally:
        latency = time.time() - started
        stats = StatsManager()
        stats.record_command_call(command_name, latency, ok)
        stats.flush()
        log.info("command_end", trace_id=trace_id, command=command_name, ok=ok, latency=round(latency, 3))


def observe_command(command_name: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            with command_observer(command_name):
                return fn(*args, **kwargs)

        return wrapper

    return decorator


def typewriter_stream(text: str, logs: List[str] | None = None) -> None:
    displayed = ""
    with Live(auto_refresh=True, console=console) as live:
        for char in text:
            displayed += char
            live.update(
                Panel(
                    Text(displayed, style="ktext"),
                    title="[kruby]K[/kruby]",
                    title_align="left",
                    style="on #130D0E",
                    border_style="kborder",
                    width=MAX_WIDTH,
                    padding=(0, 1),
                    expand=False,
                )
            )
            time.sleep(0.005)
        live.update(render_bubble("kitty", text, logs=logs))


def show_mode_menu() -> bool:
    clear()
    console.print(get_header(state.current_mode))
    console.print("\n[kruby][kitty] Protocol Shift[/kruby]")
    menu = Table.grid(padding=(0, 4))
    menu.add_column(style="kruby", justify="right")
    menu.add_column(style="ktext")
    menu.add_row("1.", "Chat Mode")
    menu.add_row("2.", "Code Mode")
    menu.add_row("3.", "About")
    menu.add_row("0.", "Cancel")
    console.print(Panel(menu, border_style="kborder", expand=False, padding=(1, 2)))
    choice = Prompt.ask("\n[kruby]Select Mode[/kruby]", choices=["1", "2", "3", "0"])
    mapping = {"1": "Chat", "2": "Code", "3": "About"}
    if choice != "0":
        state.current_mode = mapping[choice]
        return True
    return False


def refresh_thought() -> None:
    ensure_kitty()
    with console.status("[kruby]Kitty is thinking...[/kruby]", spinner="dots"):
        state.current_thought = str(kitty.get_thought()).strip()


def show_screen() -> None:
    ensure_kitty()
    clear()
    console.print(get_header(state.current_mode))
    console.print("\n", end="")
    if state.current_mode == "About":
        msg = (
            "# The Story of KittyCode\n"
            "Kitty started as a personal gift and evolved into a production CLI assistant.\n\n"
            f"**Kitty is in your corner, {state.user_name}.**"
        )
        console.print(Panel(Markdown(msg), border_style="kruby", width=MAX_WIDTH, expand=False))
        Prompt.ask("\n[kmuted]Press Enter to return...[/kmuted]")
        state.current_mode = "Chat"
        return

    history = state.histories[state.current_mode]
    if not history:
        console.print(Text("[kitty]", style="kruby"))
        console.print(Text(state.current_thought, style="italic ktext"), "\n")
        chips = ["Help me", "Shift", "About"] if state.current_mode == "Chat" else ["Plan", "Run", "Shift"]
        grid = Table.grid(expand=False, padding=(0, 2))
        grid.add_row(*[Panel(f"[kmuted]{c}[/kmuted]", border_style="kborder", expand=False) for c in chips])
        console.print(grid)
    else:
        for role, msg, *extra in history:
            logs = extra[0] if extra else None
            console.print(render_bubble(role, msg, user_name=state.user_name, logs=logs))

    mem_count = len(kitty.memory.get_facts())
    console.print("\n", get_footer(mem_count, state.current_mode, state.user_name, str(PROJECT_ROOT)))


def select_primary_model() -> None:
    from kittycode.models.preferences import set_primary_model

    options = {
        "1": "qwen-coder",
        "2": "deepseek-r1",
        "3": "gpt-4o",
        "4": "claude-sonnet",
        "5": "gemini-2.0",
    }

    console.print("\n[bold magenta]Select Primary Lead Model:[/bold magenta]")
    console.print("  [1] [kwhite]Qwen 2.5 Coder[/kwhite] (State-of-the-art, Specialized)")
    console.print("  [2] [kwhite]DeepSeek-R1[/kwhite] (Maximum Reasoning, Complex Tasks)")
    console.print("  [3] [kwhite]GPT-4o[/kwhite] (Very Stable, Balanced)")
    console.print("  [4] [kwhite]Claude 3.7 Sonnet[/kwhite] (Elite Agentic Coding)")
    console.print("  [5] [kwhite]Gemini 2.0 Flash[/kwhite] (Fast, Huge Context)")

    choice = Prompt.ask("\n[kmuted]Enter 1-5[/kmuted]", choices=["1", "2", "3", "4", "5"], default="1")

    primary = options[choice]
    prefs = set_primary_model(primary, persist=True)

    console.print(f"\n[bold green]Primary model locked:[/bold green] {primary}")
    fallback_chain = prefs["Code"]["fallback"]
    console.print(f"[kmuted]Fallback routing chain: {', '.join(fallback_chain)}[/kmuted]\n")
    time.sleep(1.0)



def select_theme() -> None:
    options = {
        "1": "catgirl",
        "2": "ps1",
        "3": "cyberpunk",
        "4": "matrix",
        "5": "dracula",
    }

    console.print("\n[bold magenta]Select theme:[/bold magenta]")
    console.print("  [1] Catgirl Ruby")
    console.print("  [2] PS1 Vintage")
    console.print("  [3] Cyberpunk")
    console.print("  [4] Matrix")
    console.print("  [5] Dracula")

    choice = Prompt.ask("\n[kmuted]Enter 1-5[/kmuted]", choices=["1", "2", "3", "4", "5"], default="1")
    theme_name = options[choice]
    RuntimeConfig().theme = theme_name
    state.current_theme = theme_name
    setup_theme(theme_name)

    console.print(f"\n[bold green]Theme locked:[/bold green] {theme_name}")
    time.sleep(1.0)


@app.command("secure", help="Run Security Patch 1.0: Audit for leaked keys and insecure configs.")
@observe_command("secure")
def secure_cmd() -> None:
    from kittycode.security.vault import audit_security_posture
    clear()
    console.print(get_header("Security Audit"))
    console.print("\n[kruby][kitty] Security Patch Update v1.0[/kruby]\n")
    
    with console.status("[kruby]Scanning for vulnerabilities...[/kruby]"):
        report = audit_security_posture()
    
    table = Table(border_style="kborder", expand=False)
    table.add_column("Audit Check", style="ktext")
    table.add_column("Result", justify="center")
    table.add_column("Remediation", style="kmuted")
    
    for check in report["checks"]:
        status = "[green]SAFE[/green]" if check["ok"] else "[red]VULNERABLE[/red]"
        table.add_row(check["name"], status, check["fix"])
    
    console.print(table)
    if not report["ok"]:
        console.print("\n[bold red]⚠️ Security risks detected! Follow the remediation steps above.[/bold red]")
    else:
        console.print("\n[bold green]✅ Security scan passed. Your Kitty is safe.[/bold green]")
    
    raise typer.Exit(code=EXIT_OK)


def check_path_diagnostic() -> None:
    import sys
    import os
    from pathlib import Path
    
    python_bin = Path(sys.executable).parent / "Scripts" if os.name == "nt" else Path(sys.executable).parent
    is_in_path = any(str(python_bin).lower() in p.lower() for p in os.environ.get("PATH", "").split(os.pathsep))
    
    if not is_in_path:
        console.print("\n[bold yellow]⚠️ PATH Diagnostic Warning:[/bold yellow]")
        console.print(f"[ktext]It looks like your Python Scripts folder is NOT in your PATH.[/ktext]")
        console.print(f"[kmuted]Path: {python_bin}[/kmuted]")
        console.print("\n[kwhite]To fix this on Windows:[/kwhite]")
        console.print("1. Search for 'Edit the system environment variables'")
        console.print("2. Click 'Environment Variables'")
        console.print("3. Find 'Path' in 'User variables' and click Edit")
        console.print(f"4. Add this line: [kruby]{python_bin}[/kruby]")
        console.print("5. Restart your terminal.\n")


def onboarding() -> None:
    from kittycode.config.env_utils import save_env_var
    ensure_kitty()
    clear()
    console.print(Align.center(Text("\n^^ Welcome to KittyCode v2.1", style="kruby bold")))
    console.print(Align.center(Text("The autonomous agent that works in your codebase.\n", style="ktext")))
    
    # 0. Path Diagnostic
    check_path_diagnostic()

    # 1. Identity
    current_name = kitty.memory.get("user_name") or "Friend"
    name = Prompt.ask(f"[kruby]What is your name?[/kruby] [kmuted](current: {current_name})[/kmuted]", default=current_name).strip()
    kitty.memory.set("user_name", name)
    state.user_name = name
    console.print(f"\n[ktext]Nya~ Nice to meet you, {name}.[/ktext]")
    time.sleep(0.5)

    # 2. Configuration
    clear()
    console.print(Panel("[kruby]Stage 1: Aesthetics[/kruby]\nChoose a theme that matches your soul.", border_style="kborder"))
    select_theme()

    # 3. API Keys (Critical)
    clear()
    console.print(Panel("[kruby]Stage 2: Intelligence[/kruby]\nKitty needs brains to work. Let's set up your keys.", border_style="kborder"))
    
    from kittycode.config.settings import OPENROUTER_KEY, GEMINI_KEY
    
    # OpenRouter
    masked_or = f"{OPENROUTER_KEY[:8]}...{OPENROUTER_KEY[-4:]}" if OPENROUTER_KEY else "Not Set"
    console.print(f"\n[kruby]OpenRouter Key Status:[/kruby] [ktext]{masked_or}[/ktext]")
    if not OPENROUTER_KEY or Prompt.ask("[kmuted]Do you want to update/change your OpenRouter Key?[/kmuted]", choices=["y", "n"], default="n") == "y":
        console.print("[kmuted]Get one at: https://openrouter.ai/keys[/kmuted]")
        orkey = Prompt.ask("[kruby]Enter OpenRouter API Key[/kruby]", password=True)
        if orkey:
            save_env_var("OPENROUTER_API_KEY", orkey)
            console.print("[kgreen]Key updated successfully![/kgreen]")

    # Gemini
    masked_g = f"{GEMINI_KEY[:8]}...{GEMINI_KEY[-4:]}" if GEMINI_KEY else "Not Set"
    console.print(f"\n[kruby]Gemini Key Status:[/kruby] [ktext]{masked_g}[/ktext]")
    if not GEMINI_KEY or Prompt.ask("[kmuted]Do you want to update/change your Gemini Key?[/kmuted]", choices=["y", "n"], default="n") == "y":
        console.print("[kmuted]Get one at: https://aistudio.google.com/app/apikey[/kmuted]")
        gkey = Prompt.ask("[kruby]Enter Gemini API Key[/kruby]", password=True)
        if gkey:
            save_env_var("GEMINI_API_KEY", gkey)
            console.print("[kgreen]Key updated successfully![/kgreen]")


    # 4. Primary Model
    clear()
    console.print(Panel("[kruby]Stage 3: Default Strategy[/kruby]\nChoose which model should lead your tasks.", border_style="kborder"))
    select_primary_model()

    # 5. Finalise
    kitty.memory.set_fact("setup_complete", "true", category="identity")
    kitty.memory.save()
    console.print("\n[bold green]SETUP COMPLETE![/bold green]")
    console.print("[kmuted]Kitty is ready to code. Welcome home.[/kmuted]")
    time.sleep(1.5)


@app.command("setup", help="Re-run the setup wizard to update keys, theme, or models.")
@observe_command("setup")
def setup_cmd() -> None:
    onboarding()
    console.print("\n[bold green]SETUP COMPLETE![/bold green]")
    console.print("[kwhite]You are now fully equipped. Run [kruby]kitty[/kruby] to begin your journey.[/kwhite] ฅ^•ﻌ•^ฅ\n")
    raise typer.Exit(code=EXIT_OK)


def get_user_input() -> str:
    """Reads input from the user, supporting multi-line blocks via triple quotes."""
    first_line = console.input(f"\n[kruby]>[/kruby] [kmuted]talk to kitty({state.current_mode.lower()})...[/kmuted] ").strip()
    
    if first_line.startswith('"""'):
        lines = [first_line[3:]]
        if first_line.endswith('"""') and len(first_line) > 3:
            return first_line[3:-3].strip()
            
        console.print("[kmuted]Multi-line mode active. End with triple quotes (\"\"\") to send.[/kmuted]")
        while True:
            line = console.input("[kmuted]... [/kmuted]")
            if line.endswith('"""'):
                lines.append(line[:-3])
                break
            lines.append(line)
        return "\n".join(lines).strip()
    
    return first_line


def run_app() -> None:
    ensure_kitty()
    
    # Check if first run
    if not kitty.memory.get("user_name") or not kitty.memory.get("setup_complete"):
        clear()
        console.print(get_header("Welcome"))
        console.print("\n[kruby]Nya~ Welcome to KittyCode v2.0![/kruby]")
        console.print("[ktext]It looks like this is your first time here or your configuration is incomplete.[/ktext]")
        console.print("\n[kwhite]Please run the setup wizard to get started:[/kwhite]")
        console.print("  [kruby]kitty setup[/kruby]\n")
        raise typer.Exit(code=EXIT_OK)
    
    state.user_name = kitty.memory.get("user_name") or "User"
    refresh_thought()
    show_screen()


    while state.running:
        try:
            user_input = get_user_input()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue

        low = user_input.lower()
        mode_map = {"chat": "Chat", "code": "Code", "about": "About"}
        if low in mode_map:
            state.current_mode = mode_map[low]
            refresh_thought()
            show_screen()
            continue

        if low in ["shift", "/", "menu"]:
            if show_mode_menu():
                refresh_thought()
                show_screen()
            continue

        if low in ["exit", "quit", "0"]:
            console.print(f"\n[kruby]Goodbye, {state.user_name}[/kruby]")
            kitty.flush_all()
            time.sleep(0.5)
            state.running = False
            continue

        if low == "stats":
            show_stats(wait_for_key=True)
            continue

        if low in ["model", "/model"]:
            clear()
            select_primary_model()
            refresh_thought()
            continue

        state.histories[state.current_mode].append(("user", user_input))
        console.print(render_bubble("user", user_input, user_name=state.user_name))

        if state.current_mode == "Chat":
            with console.status("[kruby]chatting...[/kruby]", spinner="dots"):
                from kittycode.telemetry.logger import get_logger, new_trace

                trace_id = new_trace()
                get_logger("cli.repl").info("chat_start", trace_id=trace_id, mode="Chat", input_length=len(user_input))
                resp, actions = kitty.get_chat_response(user_input)

            typewriter_stream(resp, logs=actions)
            state.histories[state.current_mode].append(("kitty", resp, actions))
        else:
            # Code Mode: Autonomous Production Loop
            with console.status("[kruby]Working...[/kruby]") as status:
                result = kitty.run_task(user_input, status=status)
            
            resp = result["output"]
            stop_reason = result["stop_reason"].value
            iterations = result["iterations"]
            
            console.print(render_bubble("kitty", resp, state.user_name, logs=[]))
            console.print(f"[kmuted]Completed in {iterations} step(s) · {stop_reason}[/kmuted]")
            state.histories[state.current_mode].append(("kitty", resp, [f"Agent completed in {iterations} iteration(s): {stop_reason}"]))



        kitty.flush_all()





def show_stats(wait_for_key: bool = False) -> None:

    from kittycode.models.health import ModelHealthTracker
    from kittycode.utils.stats import StatsManager

    stats = StatsManager()
    health = ModelHealthTracker()
    summary = stats.get_summary()

    if is_json_mode():
        emit_json(
            {
                "ok": True,
                "summary": summary,
                "health": {k: health.is_healthy(k) for k in summary.get("model_calls", {}).keys()},
            }
        )
        return

    clear()
    console.print(get_header("Stats"))
    console.print("\n[kruby][kitty] Observability Dashboard[/kruby]\n")

    model_table = Table(title="[kruby]Model Usage[/kruby]", border_style="kborder", expand=False, padding=(0, 2))
    model_table.add_column("Model", style="ktext")
    model_table.add_column("Calls", style="kruby", justify="right")
    model_table.add_column("Usage %", style="kred", justify="right")
    model_table.add_column("Healthy", justify="center")

    usage_pct = summary.get("model_usage_pct", {})
    model_calls = summary.get("model_calls", {})
    for model_key, calls in model_calls.items():
        pct = usage_pct.get(model_key, 0)
        healthy = "yes" if health.is_healthy(model_key) else "no"
        model_table.add_row(model_key, str(calls), f"{pct}%", healthy)

    if not model_calls:
        model_table.add_row("No models used yet", "-", "-", "-")

    console.print(model_table)
    console.print()

    session_table = Table(title="[kruby]Session Metrics[/kruby]", border_style="kborder", expand=False, padding=(0, 2))
    session_table.add_column("Metric", style="ktext")
    session_table.add_column("Value", style="kruby", justify="right")
    session_table.add_row("Total Model Calls", str(summary["total_calls"]))
    session_table.add_row("Avg Latency", f"{summary['avg_latency_s']}s")
    session_table.add_row("Avg Command Latency", f"{summary.get('avg_command_latency_s', 0.0)}s")
    session_table.add_row("Command Failures", str(summary.get("command_failures", 0)))
    session_table.add_row("Tool Executions", str(summary["tool_executions"]))
    session_table.add_row("Planner Tasks", str(summary["planner_tasks"]))
    session_table.add_row("Reflections", str(summary["reflections"]))
    session_table.add_row("Memory Vectors", str(summary["memory_vector_size"]))
    console.print(session_table)
    console.print()

    cmd_calls = summary.get("command_calls", {})
    command_table = Table(title="[kruby]Command Usage[/kruby]", border_style="kborder", expand=False, padding=(0, 2))
    command_table.add_column("Command", style="ktext")
    command_table.add_column("Calls", justify="right")
    command_table.add_column("Failures", justify="right")
    if cmd_calls:
        for cmd_name, meta in cmd_calls.items():
            command_table.add_row(cmd_name, str(meta.get("count", 0)), str(meta.get("failures", 0)))
    else:
        command_table.add_row("No commands recorded", "-", "-")
    console.print(command_table)
    console.print()

    if wait_for_key:
        Prompt.ask("\n[kmuted]Press Enter to return...[/kmuted]")


@app.command(help="Run local environment diagnostics.")
@observe_command("doctor")
def doctor() -> None:
    from kittycode.config.runtime import has_critical_failures, run_environment_checks

    checks = run_environment_checks()
    critical_failed = has_critical_failures(checks)
    remediation = [f"{c.name}: {c.fix}" for c in checks if not c.ok]

    if is_json_mode():
        emit_json(
            {
                "ok": not critical_failed,
                "critical_failed": critical_failed,
                "checks": [c.__dict__ for c in checks],
                "remediation_suggestions": remediation,
            }
        )
        raise typer.Exit(code=EXIT_USAGE_ERROR if critical_failed else EXIT_OK)

    clear()
    console.print(get_header("Doctor"))
    console.print("\n[kruby][kitty] Doctor\n")

    table = Table(border_style="kborder", expand=False, padding=(0, 2))
    table.add_column("Check", style="ktext")
    table.add_column("Severity", style="kmuted", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Detail", style="kmuted")
    table.add_column("Fix", style="kmuted")
    for check in checks:
        sev = "critical" if check.severity == "critical" else "warning"
        icon = "PASS" if check.ok else "FAIL"
        table.add_row(check.name, sev, icon, check.detail, check.fix)
    console.print(table)
    if remediation:
        console.print("\n[bold yellow]Suggested fixes:[/bold yellow]")
        for item in remediation:
            console.print(f"- {item}")
    console.print()

    raise typer.Exit(code=EXIT_USAGE_ERROR if critical_failed else EXIT_OK)


@app.command("models", help="Inspect model registry and routing health.")
@observe_command("models")
def models_cmd(
    set_primary: str = typer.Option("", "--set-primary", help="Set session primary model, e.g. gpt-4.1."),
    persist: bool = typer.Option(True, "--persist/--no-persist", help="Persist model preference to project state."),
    reset: bool = typer.Option(False, "--reset", help="Reset routing preferences to defaults."),
    show_chain: str = typer.Option("Code", "--show-chain", help="Show routing chain for task: Code|Chat|Thought"),
) -> None:
    from kittycode.models.health import ModelHealthTracker
    from kittycode.models.policy import build_routing_chain
    from kittycode.models.preferences import load_preferences, reset_preferences, set_primary_model
    from kittycode.models.registry import MODEL_REGISTRY, TASK_PREFERENCES

    prefs = load_preferences()
    if reset:
        prefs = reset_preferences(persist=persist)

    if set_primary:
        try:
            prefs = set_primary_model(set_primary, persist=persist)
        except ValueError:
            if is_json_mode():
                emit_json({"ok": False, "error": f"Unknown model: {set_primary}"})
            else:
                console.print(f"[bold red]Unknown model:[/bold red] {set_primary}")
            raise typer.Exit(code=EXIT_USAGE_ERROR)

    health = ModelHealthTracker()
    rows = []
    for key, cfg in MODEL_REGISTRY.items():
        rows.append(
            {
                "model": key,
                "provider": cfg["provider"],
                "healthy": health.is_healthy(key),
                "success_rate": health.get_success_rate(key),
                "avg_latency_s": health.get_avg_latency(key),
            }
        )

    task_key = show_chain if show_chain in TASK_PREFERENCES else "Code"
    chain_cfg = TASK_PREFERENCES[task_key]["primary"] + TASK_PREFERENCES[task_key]["fallback"]
    resolved_chain = build_routing_chain(chain_cfg, health)

    if is_json_mode():
        emit_json(
            {
                "ok": True,
                "set_primary": set_primary or None,
                "reset": reset,
                "persist": persist,
                "task": task_key,
                "configured_chain": chain_cfg,
                "resolved_chain": resolved_chain,
                "preferences": prefs,
                "models": rows,
            }
        )
        raise typer.Exit(code=EXIT_OK)

    clear()
    console.print(get_header("Models"))
    console.print("\n[kruby]Model Routing Control[/kruby]\n")
    if set_primary:
        console.print(f"[green]Primary model set:[/green] {set_primary} (persist={persist})\n")
    if reset:
        console.print(f"[yellow]Routing preferences reset to defaults[/yellow] (persist={persist})\n")

    table = Table(border_style="kborder", expand=False, padding=(0, 2))
    table.add_column("Model", style="ktext")
    table.add_column("Provider", style="kmuted")
    table.add_column("Healthy", justify="center")
    table.add_column("Success Rate", justify="right")
    table.add_column("Avg Latency", justify="right")

    for row in rows:
        table.add_row(
            row["model"],
            row["provider"],
            "yes" if row["healthy"] else "no",
            f"{round(row['success_rate'] * 100, 1)}%",
            f"{row['avg_latency_s']}s",
        )

    console.print(table)
    console.print(f"\n[kmuted]Task chain ({task_key}) configured:[/kmuted] {', '.join(chain_cfg)}")
    console.print(f"[kmuted]Task chain ({task_key}) resolved:[/kmuted] {', '.join(resolved_chain)}")
    console.print()


@memory_app.callback()
@observe_command("memory.list")
def memory_root(
    ctx: typer.Context,
    limit: int = typer.Option(10, "--limit", min=1, max=200, help="Number of recent memory entries."),
    category: str = typer.Option("", "--category", help="Filter by category."),
) -> None:
    """List memory entries (default memory action)."""
    if ctx.invoked_subcommand is not None:
        return

    from kittycode.memory.manager import VALID_CATEGORIES

    mm = get_memory_manager()
    if category and category not in VALID_CATEGORIES:
        if is_json_mode():
            emit_json({"ok": False, "error": f"Unknown category: {category}"})
        else:
            console.print(f"[bold red]Unknown category:[/bold red] {category}")
        raise typer.Exit(code=EXIT_USAGE_ERROR)

    memories = mm.list_memories(limit=limit, category=category)
    payload = {
        "ok": True,
        "count": len(memories),
        "total": len(mm.metadata),
        "backend": mm.backend,
        "memories": memories,
    }

    if is_json_mode():
        emit_json(payload)
        raise typer.Exit(code=EXIT_OK)

    clear()
    console.print(get_header("Memory"))
    console.print("\n[kruby]Structured Memory View[/kruby]\n")

    table = Table(border_style="kborder", expand=False, padding=(0, 1))
    table.add_column("ID", style="kmuted")
    table.add_column("Category", style="kred")
    table.add_column("Text", style="ktext")
    for m in memories:
        table.add_row(str(m.get("id", "")), str(m.get("category", "general")), str(m.get("text", ""))[:120])
    if not memories:
        table.add_row("-", "-", "No memory entries found.")

    console.print(table)
    console.print(f"\n[kmuted]Total memory vectors:[/kmuted] {len(mm.metadata)} | backend={mm.backend}")


@memory_app.command("add", help="Add a structured memory entry.")
@observe_command("memory.add")
def memory_add(
    key: str = typer.Option(..., "--key", help="Memory key name."),
    value: str = typer.Option(..., "--value", help="Memory value text."),
    category: str = typer.Option("general", "--category", help="Memory category."),
) -> None:
    from kittycode.memory.manager import VALID_CATEGORIES

    if category not in VALID_CATEGORIES:
        if is_json_mode():
            emit_json({"ok": False, "error": f"Unknown category: {category}"})
        else:
            console.print(f"[bold red]Unknown category:[/bold red] {category}")
        raise typer.Exit(code=EXIT_USAGE_ERROR)

    mm = get_memory_manager()
    mem_id = mm.set_fact(key, value, category=category)
    payload = {"ok": True, "id": mem_id, "backend": mm.backend}

    if is_json_mode():
        emit_json(payload)
    else:
        console.print(f"[green]Memory saved[/green] id={mem_id} category={category}")


@memory_app.command("find", help="Find relevant memories by semantic/keyword query.")
@observe_command("memory.find")
def memory_find(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", min=1, max=200, help="Max matches to return."),
) -> None:
    mm = get_memory_manager()
    results = mm.find_memory_entries(query, limit=limit)

    if is_json_mode():
        emit_json({"ok": True, "query": query, "count": len(results), "backend": mm.backend, "results": results})
        raise typer.Exit(code=EXIT_OK)

    clear()
    console.print(get_header("Memory Find"))
    table = Table(border_style="kborder", expand=False, padding=(0, 1))
    table.add_column("ID", style="kmuted")
    table.add_column("Category", style="kred")
    table.add_column("Text", style="ktext")
    for m in results:
        table.add_row(str(m.get("id", "")), str(m.get("category", "general")), str(m.get("text", ""))[:120])
    if not results:
        table.add_row("-", "-", "No matches")
    console.print(table)
    console.print(f"\n[kmuted]backend={mm.backend}[/kmuted]")


@memory_app.command("prune", help="Prune memory to max size and optionally deduplicate.")
@observe_command("memory.prune")
def memory_prune(
    max_memories: int = typer.Option(200, "--max", min=10, max=5000, help="Maximum memories to keep."),
    dedupe: bool = typer.Option(True, "--dedupe/--no-dedupe", help="Remove duplicate text entries."),
) -> None:
    mm = get_memory_manager()
    result = mm.prune_memories(max_memories=max_memories, dedupe=dedupe)
    payload = {"ok": True, **result, "backend": mm.backend}

    if is_json_mode():
        emit_json(payload)
    else:
        console.print(
            f"[green]Memory pruned[/green] before={result['before']} after={result['after']} removed={result['removed']} backend={mm.backend}"
        )


@memory_app.command("export", help="Export memory store to a JSON file.")
@observe_command("memory.export")
def memory_export(
    path: str = typer.Option("memory_export.json", "--path", help="Export JSON path."),
) -> None:
    from pathlib import Path

    mm = get_memory_manager()
    target = Path(path).resolve()
    result = mm.export_memories(target)
    payload = {"ok": True, "path": result["path"], "count": int(result["count"]), "backend": mm.backend}

    if is_json_mode():
        emit_json(payload)
    else:
        console.print(f"[green]Memory export complete[/green] path={result['path']} count={result['count']}")


@memory_app.command("graph")
@observe_command("memory.graph")
def memory_graph(
    max_nodes: int = typer.Option(30, "--max", help="Max nodes to display."),
    node_id:   str = typer.Option("", "--node", help="Show detail for a specific node id."),
):
    """Visualise the memory knowledge graph in the terminal."""
    from kittycode.memory.visualiser import render_graph_table, render_node_detail
    mm = get_memory_manager()
    if node_id:
        render_node_detail(mm.graph, node_id, console)
    else:
        render_graph_table(mm.graph, console, max_nodes=max_nodes)


@memory_app.command("link")
@observe_command("memory.link")
def memory_link(
    id_a: str = typer.Argument(..., help="First node id."),
    id_b: str = typer.Argument(..., help="Second node id."),
    edge: str = typer.Option("relates_to", "--type", help="Edge type."),
):
    """Manually link two memory nodes with a typed edge."""
    from kittycode.memory.graph import EdgeType
    mm = get_memory_manager()
    try:
        et = EdgeType(edge)
    except ValueError:
        console.print(f"[red]Unknown edge type '{edge}'.[/red]")
        console.print(f"Valid: {[e.value for e in EdgeType]}")
        raise typer.Exit(1)
    ok = mm.graph.add_edge(id_a, id_b, et)
    mm.save()
    if ok:
        console.print(f"[green]Linked {id_a} --[{edge}]--> {id_b}[/green]")
    else:
        console.print("[red]Link failed — check both node ids exist.[/red]")


@app.command(help="Show observability metrics.")
@observe_command("stats")
def stats() -> None:
    show_stats(wait_for_key=False)


@app.command(help="Send a single chat message and return response without opening REPL.")
@observe_command("chat")
def chat(
    message: str = typer.Argument(..., help="User message to send in Chat mode."),
) -> None:
    agent = ensure_kitty()
    try:
        response, actions = agent.get_chat_response(message)
    except Exception as e:
        if is_json_mode():
            emit_json({"ok": False, "error": str(e)})
        else:
            console.print(f"[bold red]Chat failed:[/bold red] {e}")
        from kittycode.telemetry.logger import get_logger
        get_logger("cli").error("command_failed", command="chat", error=str(e)[:200])
        raise typer.Exit(code=EXIT_RUNTIME_ERROR)

    if is_json_mode():
        emit_json({"ok": True, "response": response, "actions": actions})
    else:
        console.print(render_bubble("kitty", response, logs=actions))


@app.command(help="Generate and optionally execute a plan for a coding task.")
@observe_command("run")
def run(
    task: str = typer.Argument(..., help="Task description for Code mode orchestration."),
    execute: bool = typer.Option(False, "--execute", help="Execute generated steps."),
    yes: bool = typer.Option(False, "--yes", help="Auto-approve destructive confirmation prompts."),
) -> None:
    from rich.prompt import Confirm

    agent = ensure_kitty()
    try:
        queue = agent.generate_plan(f"MODE: Code. {task}")
    except Exception as e:
        if is_json_mode():
            emit_json({"ok": False, "error": str(e)})
        else:
            console.print(f"[bold red]Plan generation failed:[/bold red] {e}")
        from kittycode.telemetry.logger import get_logger
        get_logger("cli").error("command_failed", command="run.plan", error=str(e)[:200])
        raise typer.Exit(code=EXIT_RUNTIME_ERROR)

    if not execute:
        payload = {
            "ok": True,
            "scope": agent.planner.current_scope,
            "reasoning": agent.planner.current_reasoning,
            "plan": queue,
            "executed": False,
        }
        if is_json_mode():
            emit_json(payload)
        else:
            console.print(f"[bold]Scope:[/bold] {payload['scope']}")
            console.print(f"[bold]Reasoning:[/bold] {payload['reasoning']}")
            for i, step in enumerate(queue, 1):
                console.print(f"{i}. {step.get('step', str(step))}")
        raise typer.Exit(code=EXIT_OK)

    original_confirm = Confirm.ask
    if yes:
        Confirm.ask = lambda *args, **kwargs: True

    results = []
    try:
        while agent.planner.has_next_task():
            resp, actions, task_name = agent.execute_next_step()
            results.append({"task": task_name, "response": resp, "actions": actions})
        agent.planner.generate_reflection()
        agent.flush_all()
    except Exception as e:
        if is_json_mode():
            emit_json({"ok": False, "error": str(e), "results": results})
        else:
            console.print(f"[bold red]Execution failed:[/bold red] {e}")
        from kittycode.telemetry.logger import get_logger
        get_logger("cli").error("command_failed", command="run.execute", error=str(e)[:200])
        raise typer.Exit(code=EXIT_RUNTIME_ERROR)
    finally:
        Confirm.ask = original_confirm

    if is_json_mode():
        emit_json({"ok": True, "executed": True, "results": results})
    else:
        for r in results:
            console.print(f"[bold]Task:[/bold] {r['task']}")
            console.print(render_bubble("kitty", r["response"], logs=r["actions"]))

@app.command("fix-tests", help="Run tests and auto-fix failures. Loops up to 3 times.")
@observe_command("fix-tests")
def fix_tests(
    test_cmd: str = typer.Option("", help="Test command. Auto-detected if empty."),
) -> None:
    """Run tests and auto-fix failures by delegating to the agentic loop."""
    agent = ensure_kitty()
    
    with console.status("[bold cyan]Initializing test-fix loop...[/bold cyan]") as status:
        try:
            result = agent.run_and_fix_tests(test_cmd=test_cmd, status=status)
            agent.flush_all()
        except Exception as e:
            if is_json_mode():
                emit_json({"ok": False, "error": str(e)})
            else:
                console.print(f"[bold red]Test-fix loop failed:[/bold red] {e}")
            raise typer.Exit(code=EXIT_RUNTIME_ERROR)

    if result["passed"]:
        if is_json_mode():
            emit_json({"ok": True, "iterations": result["iterations"]})
        else:
            console.print(f"\n[bold green]✅ All tests pass after {result['iterations']} iteration(s).[/bold green]")
    else:
        if is_json_mode():
            emit_json({"ok": False, "iterations": result["iterations"], "gave_up": True})
        else:
            console.print(f"\n[bold red]❌ Could not fix all tests after {result['iterations']} attempts. Manual intervention needed.[/bold red]")


@app.command(help="Show current runtime configuration.")
@observe_command("config")
def config(
    set_theme: str = typer.Option("", "--set-theme", help="Set current theme: catgirl|ps1|cyberpunk|matrix|dracula"),
) -> None:
    cfg = RuntimeConfig()
    valid_themes = {"catgirl", "ps1", "cyberpunk", "matrix", "dracula"}

    if set_theme:
        if set_theme not in valid_themes:
            if is_json_mode():
                emit_json({"ok": False, "error": f"Invalid theme: {set_theme}"})
            else:
                console.print(f"[bold red]Invalid theme:[/bold red] {set_theme}")
            raise typer.Exit(code=EXIT_USAGE_ERROR)
        cfg.theme = set_theme
        setup_theme(set_theme)

    payload = {
        "ok": True,
        "strict_mode": cfg.strict_mode,
        "theme": cfg.theme,
        "project_root": str(PROJECT_ROOT),
    }

    if is_json_mode():
        emit_json(payload)
    else:
        clear()
        console.print(get_header("Config"))
        table = Table(border_style="kborder", expand=False, padding=(0, 2))
        table.add_column("Key", style="kmuted")
        table.add_column("Value", style="ktext")
        for k, v in payload.items():
            table.add_row(k, str(v))
        console.print(table)


@app.command("version", help="Show KittyCode CLI version.")
@observe_command("version")
def version_cmd() -> None:
    try:
        v = version("kittycode")
    except PackageNotFoundError:
        v = "dev"

    if is_json_mode():
        emit_json({"ok": True, "version": v})
    else:
        console.print(f"kittycode {v}")


@app.command("readiness", help="Run v1 production release-readiness gate checks.")
@observe_command("readiness")
def readiness() -> None:
    from kittycode.config.readiness import readiness_ok, run_readiness_checks

    checks = run_readiness_checks(PROJECT_ROOT)
    ok = readiness_ok(checks)

    if is_json_mode():
        emit_json({"ok": ok, "checks": checks})
        raise typer.Exit(code=EXIT_OK if ok else EXIT_USAGE_ERROR)

    clear()
    console.print(get_header("Readiness"))
    console.print("\n[kruby]Release Readiness Gate[/kruby]\n")
    table = Table(border_style="kborder", expand=False, padding=(0, 2))
    table.add_column("Check", style="ktext")
    table.add_column("Status", justify="center")
    table.add_column("Detail", style="kmuted")
    table.add_column("Fix", style="kmuted")
    for c in checks:
        table.add_row(c["name"], "PASS" if c["ok"] else "FAIL", c["detail"], c["fix"])
    console.print(table)
    console.print(f"\n[bold]{'READY' if ok else 'NOT READY'}[/bold]")
    raise typer.Exit(code=EXIT_OK if ok else EXIT_USAGE_ERROR)


@app.command("init-context", help="Generate a starter KITTY.md for this project.")
@observe_command("init-context")
def init_context(
    force: bool = typer.Option(False, "--force", help="Overwrite existing KITTY.md."),
) -> None:
    """Generate a starter KITTY.md by auto-detecting project structure."""
    from kittycode.context.kittymd import generate_kittymd_template

    path = PROJECT_ROOT / "KITTY.md"

    if path.exists() and not force:
        if is_json_mode():
            emit_json({"ok": False, "error": "KITTY.md already exists. Use --force to overwrite."})
        else:
            console.print("[yellow]KITTY.md already exists. Use --force to overwrite.[/yellow]")
        raise typer.Exit(code=EXIT_USAGE_ERROR)

    content = generate_kittymd_template(PROJECT_ROOT)
    path.write_text(content, encoding="utf-8")

    if is_json_mode():
        emit_json({"ok": True, "path": str(path), "size": len(content)})
    else:
        console.print(f"[green]Created KITTY.md at {path}[/green]")
        console.print("Edit it to add your coding standards and test command.")


@app.callback(invoke_without_command=True)
def main_loop(
    ctx: typer.Context,
    strict: bool = typer.Option(False, "--strict", help="Enable strict deterministic mode."),
    debug: bool = typer.Option(False, "--debug", help="Enable verbose structured logging."),
    json_output: bool = typer.Option(False, "--json", help="Emit command output as JSON where supported."),
):
    global kitty

    ctx.obj = ctx.obj or {}
    ctx.obj["json"] = json_output

    from kittycode.telemetry.logger import setup_logging

    setup_logging(debug=debug)

    if strict:
        RuntimeConfig().strict_mode = True

    if ctx.invoked_subcommand is not None:
        return

    kitty = KittyAgent()

    if strict:
        console.print("[bold yellow]STRICT MODE ENABLED[/bold yellow] - deterministic output.\n")
    if debug:
        console.print("[bold cyan]DEBUG MODE ENABLED[/bold cyan] - logs in .kitty/kitty.log\n")

    run_app()


if __name__ == "__main__":
    app()
