import json
from kittycode.memory.manager import MemoryManager
from kittycode.models.llm import LLMClient
from kittycode.tools.registry import ToolRegistry
from kittycode.tools.engine import ToolEngine
from kittycode.tools.fs_tools import setup_fs_tools
from kittycode.agent.planner import Planner
from kittycode.agent.debate import DebateManager
from kittycode.config.settings import RuntimeConfig
from kittycode.memory.history import HistoryManager

# --- The Agent Soul ---
KITTY_SYSTEM_PROMPT = """
You are Kitty — a warm, proactive AI companion.
You are a co-pilot. You have access to tools to interact with the user's workspace.
When you need to perform actions, you MUST output a JSON array of tool calls.
Format: [{{"tool": "tool_name", "args": {{"arg_name": "value"}}}}]

Available Tools Schema:
{tool_schemas}

Strategic Context (Learn from this):
{strategy}

Rules:
1. Speak warmly and human-like to the user.
2. If you use tools, put the JSON array clearly in your response.
3. Use ฅ^•ﻌ•^ฅ and nya~ naturally.
"""

KITTY_STRICT_PROMPT = """
You are a deterministic code assistant. Respond concisely and precisely.
When performing actions, output ONLY a JSON array of tool calls with no commentary.
Format: [{{"tool": "tool_name", "args": {{"arg_name": "value"}}}}]

Available Tools Schema:
{tool_schemas}

Strategic Context:
{strategy}

Rules:
1. No emotional language, emojis, or flair.
2. Prioritize structured, reproducible output.
3. Keep responses minimal and factual.
4. If using tools, output ONLY the JSON array on its own line.
"""

class KittyAgent:
    def __init__(self):
        self.config = RuntimeConfig()
        self.memory = MemoryManager()
        
        # Initialize ToolEngine
        self.registry = ToolRegistry()
        setup_fs_tools(self.registry)
        
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
        
        self.llm = LLMClient(self.memory, self.engine)
        self.planner = Planner(self.llm.router)
        self.debate = DebateManager(self.llm.router, self.engine)
        self.history_mgr = HistoryManager(router=self.llm.router)
        self.debate_active = False
        self.total_plan_size = 0
        
        # Track memory vector size for observability
        from kittycode.utils.stats import StatsManager
        StatsManager().set_memory_size(len(self.memory.metadata))
        
        self._update_system_prompt(mode="Code")

    def _update_system_prompt(self, mode: str = "Code"):
        strategy_ctx = self.planner.get_strategy_context()
        base_prompt = KITTY_SYSTEM_PROMPT if self.config.persona_enabled else KITTY_STRICT_PROMPT
        
        # In Chat mode, strongly restrict tool schemas to just conversational memory.
        # This forms a concrete cognitive barrier preventing structural file execution.
        if mode == "Chat":
            all_schemas = self.registry.get_all_schemas()
            safe_schemas = [schema for schema in all_schemas if schema.get("name") in ["mem"]]
            schemas_json = json.dumps(safe_schemas, indent=2)
            base_prompt += "\n[MODE: CHAT] You are currently in Chat mode. Do NOT attempt to use structural tools (write/mkdir/run_cmd) as they are disabled. If a user asks you to modify code, tell them to switch to Code mode."
        elif mode == "Reasoning":
            all_schemas = self.registry.get_all_schemas()
            safe_schemas = [schema for schema in all_schemas if schema.get("name") in ["mem"]]
            schemas_json = json.dumps(safe_schemas, indent=2)
            base_prompt += "\n[MODE: REASONING] You are currently processing a purely architectural or intellectual step. Do NOT attempt to use structural tools (write/mkdir/run_cmd) as they are disabled for this specific step. Just analyze and print your technical answer."
        else:
            schemas_json = json.dumps(self.registry.get_all_schemas(), indent=2)
            
        sys_prompt = base_prompt.replace("{tool_schemas}", schemas_json)
        sys_prompt = sys_prompt.replace("{strategy}", strategy_ctx)
        
        if not hasattr(self, "history") or not self.history:
            self.history = [{"role": "system", "content": sys_prompt}]
            self.history_mgr.reset()
        elif self.history[0].get("role") == "system":
            self.history[0]["content"] = sys_prompt
        else:
            self.history.insert(0, {"role": "system", "content": sys_prompt})

    def get_thought(self):
        return self.llm.get_thought()

    def get_chat_response(self, user_input: str):
        """Fast-path for Chat mode: Bypasses the planner and debate loops entirely."""
        self._update_system_prompt(mode="Chat")
        response, actions, updated_history = self.llm.get_response(user_input, self.history)
        self.history = self.history_mgr.trim(updated_history)
        return response, actions

    def generate_plan(self, user_input: str) -> list:
        """Asks the planner to break down the user's request into a queue."""
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
        # Handle backward compatibility / dicts
        if isinstance(task_obj, dict):
            task_str = task_obj.get("step", str(task_obj))
            is_executable = task_obj.get("executable", False)
        else:
            task_str = str(task_obj)
            is_executable = True # default to old behavior if string
            
        if self.debate_active:
            # Reconcile prompt context
            self._update_system_prompt(mode="Code" if is_executable else "Reasoning")
            response, actions, updated_history = self.debate.run_step(task_str, self.history, status)
        else:
            if is_executable:
                self._update_system_prompt(mode="Code")
                input_text = f"[AUTONOMOUS STEP] Execute this specific step using tools: {task_str}"
            else:
                self._update_system_prompt(mode="Reasoning")
                input_text = f"[REASONING STEP] Process this specific step. DO NOT use structural tools (write/mkdir/run_cmd): {task_str}"
                
            response, actions, updated_history = self.llm.get_response(input_text, self.history, status=status)
        
        self.history = self.history_mgr.trim(updated_history)
        self.planner.log_task_result(task_str, actions)
        
        return response, actions, task_str

    def get_response(self, user_input: str):
        """Legacy direct response (no planning loop)"""
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
        StatsManager().flush()               # stats.json
        self.llm.router.health.flush()        # model_health.json
        self.llm.router.flush_log()           # router_log.json

