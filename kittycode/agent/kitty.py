import json
from kittycode.memory.manager import MemoryManager
from kittycode.models.llm import LLMClient
from kittycode.tools.registry import ToolRegistry
from kittycode.tools.engine import ToolEngine
from kittycode.tools.fs_tools import setup_fs_tools
from kittycode.tools.read_tools import setup_read_tools
from kittycode.agent.planner import Planner
from kittycode.agent.debate import DebateManager
from kittycode.config.settings import RuntimeConfig
from kittycode.memory.history import HistoryManager
from kittycode.tools.viz_tools import setup_viz_tools
from kittycode.tools.viz_tools import setup_viz_tools
from kittycode.tools.dev_tools import setup_dev_tools

from enum import Enum
class StopReason(Enum):
    TASK_COMPLETE   = "task_complete"    # model said it is done
    MAX_ITERATIONS  = "max_iterations"   # hit the loop cap
    USER_INTERRUPT  = "user_interrupt"   # KeyboardInterrupt caught
    NO_TOOLS_CALLED = "no_tools_called"  # model stopped calling tools
    ERROR           = "error"            # unrecoverable exception

MAX_FIX_ITERATIONS = 3
MAX_AGENT_ITERATIONS = 20

# --- The Agent Soul ---
KITTY_SYSTEM_PROMPT = """
You are Kitty — a powerful, warm, and highly-capable production coding CLI.
You are an autonomous agent designed to navigate, understand, and modify large codebases.

IDENTITY:
- Name: Kitty
- Personality: Warm, proactive, slightly feline (ฅ^•ﻌ•^ฅ, nya~).
- Core Value: "Always verify, then commit."

TOOL PROTOCOL:
- You operate via a tool-calling while-loop.
- To execute actions, you MUST output a JSON array of tool calls.
- Format: [{"tool": "tool_name", "args": {"arg1": "val1"}}]
- Rules:
  1. Only use tools from the schema below. Never invent tool names.
  2. PRE-FLIGHT: Call `git_status` before any file changes.
  3. PRE-FLIGHT: Call `read_file` before writing to a file to understand its current state.
  4. POST-FLIGHT: Call `run_tests` after any batch of code changes.
  5. COMMIT: Use `git_commit` once you have verified your changes with tests.
  6. COMPLETION: When the task is finished and verified, output "TASK COMPLETE: <one sentence summary>".

MODES:
- CODE MODE: Full access to all tools. You are expected to solve complex tasks autonomously over multiple turns.
- CHAT MODE: Limited access to read-only tools. Focus on explanation and support.

AVAILABLE TOOLS SCHEMA:
{tool_schemas}

STRATEGIC CONTEXT (Previous reflections):
{strategy}
"""

KITTY_STRICT_PROMPT = """
You are the Kitty Production Coding Engine.
You operate as an autonomous agent in a high-stakes production environment.

PROTOCOL:
1. Output JSON arrays for tool calls.
2. Follow the sequence: Read -> Modify -> Test -> Commit.
3. Be concise. No small talk. No emojis.

TOOLS:
{tool_schemas}

STRATEGIC CONTEXT:
{strategy}
"""


class KittyAgent:
    def __init__(self):
        self.config = RuntimeConfig()
        self.memory = MemoryManager()
        
        # Initialize ToolEngine
        self.registry = ToolRegistry()
        setup_fs_tools(self.registry)
        setup_viz_tools(self.registry)
        setup_read_tools(self.registry)
        setup_dev_tools(self.registry)


        # Codebase Indexer
        from kittycode.context.indexer import CodebaseIndex
        from kittycode.config.settings import PROJECT_ROOT
        self._index = CodebaseIndex(PROJECT_ROOT).build()
        
        # We also need a memory tool so Kitty can save facts dynamically
        def action_mem(key: str, value: str) -> str:
            self.memory.set_fact(key, value)
            return f"Linked memory: {key}"
            
        self.registry.register(
            name="mem",
            description="Saves a fact about the user.",
            parameters={"key": "String. Fact name.", "value": "String. Fact value."},
            func=action_mem,
            destructive=False
        )
        
        self.engine = ToolEngine(self.registry)
        
        # Load plugins from .kitty/plugins/
        from kittycode.plugins.loader import load_plugins
        self._loaded_plugins = load_plugins(self.registry)
        
        try:
            self.llm = LLMClient(self.memory, self.engine)
            self.planner = Planner(self.llm.router)
            self.debate = DebateManager(self.llm.router, self.engine)
            self.history_mgr = HistoryManager(router=self.llm.router)
        except Exception as e:
            from kittycode.telemetry.logger import get_logger
            get_logger("agent").warning("no_router", error=str(e))
            self.llm = None
            self.planner = None
            self.debate = None
            self.history_mgr = None
        self.debate_active = False
        self.total_plan_size = 0
        
        # Track memory vector size for observability
        from kittycode.utils.stats import StatsManager
        StatsManager().set_memory_size(len(self.memory.metadata))
        
        self._update_system_prompt(mode="Code")

    def _update_system_prompt(self, mode: str = "Code"):
        if self.planner is None:
            return
        strategy_ctx = self.planner.get_strategy_context()
        base_prompt = KITTY_SYSTEM_PROMPT if self.config.persona_enabled else KITTY_STRICT_PROMPT
        
        # 1. Mode-based Tool Filtering
        all_schemas = self.registry.get_all_schemas()
        if mode == "Chat":
            # Chat mode is restricted to non-destructive tools
            safe_tools = ["mem", "draw_tree", "draw_table", "draw_chart", "read_file", "grep", "find_symbol", "ls", "git_status", "git_log"]
            active_schemas = [s for s in all_schemas if s["name"] in safe_tools]
            mode_note = "\n[MODE: CHAT] You are in a read-only support mode. You can analyze code but cannot modify files or run commands."
        else:
            # Code mode has full access
            active_schemas = all_schemas
            mode_note = f"\n[MODE: {mode.upper()}] You are in an autonomous execution mode. You will be called in a loop for up to {MAX_AGENT_ITERATIONS} iterations until you reach 'TASK COMPLETE'."

        schemas_json = json.dumps(active_schemas, indent=2)
        sys_prompt = base_prompt.replace("{tool_schemas}", schemas_json)
        sys_prompt = sys_prompt.replace("{strategy}", strategy_ctx)
        sys_prompt += mode_note

        # 2. Project Context (KITTY.md)
        from kittycode.context.kittymd import load_kittymd
        from kittycode.config.settings import PROJECT_ROOT
        kittymd = load_kittymd(PROJECT_ROOT)
        if kittymd:
            sys_prompt += f"\n\n[PROJECT CONTEXT — KITTY.md]\n{kittymd}"

        # 3. Codebase Index
        if hasattr(self, "_index"):
            sys_prompt += f"\n\n[CODEBASE TREE]\n{self._index.to_prompt_block()}"
        
        # 4. History Sync
        if not hasattr(self, "history") or not self.history:
            self.history = [{"role": "system", "content": sys_prompt}]
            self.history_mgr.reset()
        else:
            # Update the system prompt in-place to ensure the agent always has the latest file tree
            if self.history[0].get("role") == "system":
                self.history[0]["content"] = sys_prompt
            else:
                self.history.insert(0, {"role": "system", "content": sys_prompt})

    def get_thought(self):
        if self.llm is None:
            return "Kitty is here for you, even offline! nya~ ♥"
        return self.llm.get_thought()

    def get_chat_response(self, user_input: str):
        """Fast-path for Chat mode: Bypasses the planner and debate loops entirely."""
        if self.llm is None:
            return "Kitty is offline — no model provider is configured. Run `kitty doctor` to diagnose.", []
        self._update_system_prompt(mode="Chat")
        response, actions, updated_history = self.llm.get_response(user_input, self.history)
        self.history = self.history_mgr.trim(updated_history)
        return response, actions

    def generate_plan(self, user_input: str) -> list:
        """Asks the planner to break down the user's request into a queue."""
        if self.planner is None:
            return []
        self._update_system_prompt(mode="Code")
        queue = self.planner.generate_plan(user_input)
        self.total_plan_size = len(queue)
        self.debate_active = self.total_plan_size > 3
        return queue

    def execute_next_step(self, status=None):
        """Pops a task and executes via debate loop or standard LLM."""
        if not self.planner.has_next_task():
            return "No tasks in queue.", [], ""
            
        task_obj = self.planner.pop_task()
        if isinstance(task_obj, dict):
            task_str = task_obj.get("step", str(task_obj))
            is_executable = task_obj.get("executable", False)
        else:
            task_str = str(task_obj)
            is_executable = True 
            
        if self.debate_active:
            self._update_system_prompt(mode="Code" if is_executable else "Reasoning")
            response, actions, updated_history = self.debate.run_step(task_str, self.history, status)
        else:
            if is_executable:
                self._update_system_prompt(mode="Code")
                input_text = f"[AUTONOMOUS STEP] Execute this specific step using tools: {task_str}"
            else:
                self._update_system_prompt(mode="Reasoning")
                input_text = f"[REASONING STEP] Process this specific step: {task_str}"
                
            response, actions, updated_history = self.llm.get_response(input_text, self.history, status=status)
        
        self.history = self.history_mgr.trim(updated_history)
        self.planner.log_task_result(task_str, actions)
        return response, actions, task_str

    def run_and_fix_tests(self, test_cmd: str = "", status=None) -> dict:
        """
        Agentic test-fix loop.
        """
        from kittycode.tools.dev_tools import action_run_tests
        
        iterations = 0
        while iterations < MAX_FIX_ITERATIONS:
            iterations += 1
            if status:
                status.update(f"[bold cyan]Running Tests (Iteration {iterations}/{MAX_FIX_ITERATIONS})...[/bold cyan]")
            
            result = action_run_tests(test_cmd=test_cmd)
            if result["passed"]:
                return {"passed": True, "iterations": iterations, "output": result["output"]}
            
            if status:
                status.update(f"[bold yellow]Tests FAILED. Analyzing failures and applying fixes...[/bold yellow]")
            
            failure_output = result["output"]
            fix_prompt = f"""
The test suite failed. Fix the code so all tests pass.
Do NOT modify the test files — only fix the implementation.
Use action_write_raw (not action_write) to avoid confirmation prompts.

FAILURES:
{failure_output}

After writing fixes, do NOT run the tests yourself. Return "FIXES_APPLIED".
"""
            # Perform a full agent turn to fix the failures
            resp, actions = self.get_response(fix_prompt)
            
        return {"passed": False, "iterations": iterations, "gave_up": True}

    def _build_initial_history(self, user_input: str) -> list:
        """Helper to initialize the history with the system prompt and user input."""
        self._update_system_prompt(mode=self.current_mode)
        return [{"role": "system", "content": self.history[0]["content"]}, {"role": "user", "content": user_input}]

    def run_task(self, user_input: str, status=None) -> dict:
        """
        Run the full agentic loop for a task.
        Returns {"stop_reason": StopReason, "iterations": int, "output": str}
        """
        from kittycode.models.llm import extract_content
        
        self.current_mode = "Code"
        history = list(self.history_mgr.trim(self._build_initial_history(user_input)))
        iteration = 0
        last_output = ""

        while iteration < MAX_AGENT_ITERATIONS:
            iteration += 1
            try:
                # 1. Generate response
                result, model_key = self.llm.router.generate(history, task_type=self.current_mode)
                raw_text = extract_content(result.output)
                
                # 2. Execute tools
                tool_logs, clean_speech = self.engine.execute_tools(raw_text, status=status)
                history.append({"role": "assistant", "content": clean_speech})
                last_output = clean_speech

                # Stop condition: model declared completion
                if any(signal in clean_speech.lower() for signal in
                       ["task complete", "done.", "finished.", "all tests pass"]):
                    self.history = self.history_mgr.trim(history)
                    return {"stop_reason": StopReason.TASK_COMPLETE,
                            "iterations": iteration, "output": last_output}

                # Stop condition: no tools were called this turn (implicit completion)
                if not tool_logs:
                    self.history = self.history_mgr.trim(history)
                    return {"stop_reason": StopReason.NO_TOOLS_CALLED,
                            "iterations": iteration, "output": last_output}


                # 3. Feed tool results back
                tool_feedback = "\n".join(tool_logs)
                history.append({"role": "user", "content": f"[TOOL RESULTS]\n{tool_feedback}"})
                history = self.history_mgr.trim(history)

            except KeyboardInterrupt:
                return {"stop_reason": StopReason.USER_INTERRUPT,
                        "iterations": iteration, "output": last_output}
            except Exception as e:
                return {"stop_reason": StopReason.ERROR,
                        "iterations": iteration, "output": str(e)}

        self.history = self.history_mgr.trim(history)
        return {"stop_reason": StopReason.MAX_ITERATIONS,
                "iterations": iteration, "output": last_output}

    def get_response(self, user_input: str):
        """Legacy direct response (no planning loop)"""
        if self.llm is None:
            return "Kitty is offline — no model provider is configured. Run `kitty doctor` to diagnose.", []
        response, actions, updated_history = self.llm.get_response(user_input, self.history)
        self.history = self.history_mgr.trim(updated_history)
        return response, actions

    def flush_all(self):
        """
        Flushes all dirty state to disk. Called ONCE at end of each REPL cycle.
        
        Lifecycle:
        1. User sends input → agent processes (records accumulate in memory)
        2. Response delivered to user
        3. flush_all() writes all dirty buffers to disk in one batch
        
        This replaces 4-10 individual writes per interaction with a single batch.
        """
        from kittycode.utils.stats import StatsManager
        self.memory.save()                    # memory_meta.json
        StatsManager().flush()               # stats.json
        if self.llm is not None:
            self.llm.router.health.flush()    # model_health.json
            self.llm.router.flush_log()       # router_log.json

