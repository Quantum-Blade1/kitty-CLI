import json
import logging
import re
import yaml
from typing import List, Dict, Optional
from kittycode.config.settings import STRATEGY_FILE
from kittycode.utils.stats import StatsManager

logger = logging.getLogger(__name__)

PLANNER_PROMPT = """
You are the architectural engine of kitty.
Analyze the user's request and determine its Scope before planning steps.
- Scope "Ask": The user just wants a piece of code, explanation, or script to read in the chat. Do NOT use tools.
- Scope "Project": The user wants you to actively modify the file system, compile code, or run structural commands.
  - CRITICAL CONSTRAINT: For a "Project", you MUST provide a queue of minimum 2 and maximum 6 concrete steps. Do NOT exceed 6 steps.

Output exactly a JSON object. Do not output anything else.
{
  "scope": "Ask", // or "Project"
  "reasoning": "brief explanation of why this scope was chosen",
  "queue": [
    {"step": "Step 1 description", "executable": false},
    {"step": "Step 2 description", "executable": true}
  ]
}
If no steps are needed, output {"scope": "Ask", "reasoning": "None required", "queue": []}
"""

REFLECTION_PROMPT = """
You are Kitty's internal reflection module.
Review the original overarching goal, the steps you took, and the outcomes.
Write a 2-3 sentence internal note on:
1. What worked well.
2. What mistakes or errors occurred.
3. A strategy for doing this better next time.
This will be saved to your long-term strategy log to make you smarter.
"""

class Planner:
    def __init__(self, router):
        self.router = router
        self.queue: List[Dict] = []
        self.strategy_file = STRATEGY_FILE
        self._load_strategies()
        self.current_goal = None
        self.current_scope = "Project"
        self.current_reasoning = ""
        self.task_history = []

    def _load_strategies(self):
        self.strategies = []
        if self.strategy_file.exists():
            try:
                with open(self.strategy_file, "r") as f:
                    self.strategies = json.load(f)
            except Exception as e:
                logger.error(f"Error loading strategies: {e}")

    def _save_strategies(self):
        try:
            with open(self.strategy_file, "w") as f:
                json.dump(self.strategies, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving strategies: {e}")

    def _extract_content(self, output):
        if isinstance(output, list) and len(output) > 0: output = output[-1]
        if isinstance(output, dict): return output.get("content", str(output))
        return str(output)

    def generate_plan(self, user_request: str) -> List[Dict]:
        """Ask the LLM to break the request into a queue."""
        self.current_goal = user_request
        self.current_scope = "Project"
        self.current_reasoning = ""
        self.task_history = []
        
        prompt = [
            {"role": "system", "content": PLANNER_PROMPT},
            {"role": "user", "content": user_request}
        ]
        
        try:
            result, _ = self.router.generate(prompt, task_type="Thought")
            output_text = self._extract_content(result.output).strip()
            
            # Find the first { and the last } to extract the full JSON object block
            start_idx = output_text.find('{')
            end_idx = output_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = output_text[start_idx:end_idx+1]
                
                # Pre-processing heuristics for LLM hallucinations
                # 1. Escaping raw Windows paths (C:\foo -> C:\\foo)
                json_str = re.sub(r'\\([^"\\/bfnrtu])', r'\\\\\1', json_str)
                
                # 2. Aggressively sanitize unescaped inner quotes inside tricky string fields.
                def escape_inner_quotes(match):
                    prefix = match.group(1) # "key": "
                    content = match.group(2) # inner content
                    suffix = match.group(3) # "
                    # Escape any unescaped double quotes inside the content
                    escaped_content = re.sub(r'(?<!\\)"', r'\"', content)
                    return f"{prefix}{escaped_content}{suffix}"
                
                # Sanitize the "command" value and the new "reasoning" value
                json_str = re.sub(r'("command"\s*:\s*")(.*?)("\s*\}|"\s*,)', escape_inner_quotes, json_str, flags=re.DOTALL)
                json_str = re.sub(r'("reasoning"\s*:\s*")(.*?)("\s*,)', escape_inner_quotes, json_str, flags=re.DOTALL)
                
                try:
                    # YAML is significantly more resilient to LLM escaping flaws
                    parsed_plan = yaml.safe_load(json_str)
                    
                    if not isinstance(parsed_plan, dict):
                        # Fallback for old models outputting raw arrays
                        self.queue = parsed_plan if isinstance(parsed_plan, list) else []
                        return self.queue
                        
                    self.current_scope = parsed_plan.get("scope", "Project")
                    self.current_reasoning = parsed_plan.get("reasoning", "")
                    tasks = parsed_plan.get("queue", [])
                    
                    # Ensure queue objects are clean dicts matching the {step, executable} contract
                    clean_tasks = []
                    if isinstance(tasks, list):
                        for t in tasks:
                            if isinstance(t, dict) and "step" in t:
                                is_exec = False if self.current_scope == "Ask" else bool(t.get("executable", False))
                                clean_tasks.append({
                                    "step": str(t["step"]),
                                    "executable": is_exec
                                })
                            elif isinstance(t, str):
                                clean_tasks.append({"step": t, "executable": False})
                    
                    self.queue = clean_tasks
                except Exception as e:
                    logger.error(f"Failed to parse inner YAML: {e}\nString was: {json_str}")
                    self.queue = []
            else:
                logger.error(f"No JSON object brackets found in output: {output_text}")
                self.queue = []
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            self.queue = []
            
        return self.queue

    def has_next_task(self) -> bool:
        return len(self.queue) > 0

    def pop_task(self) -> Optional[Dict]:
        if self.has_next_task():
            StatsManager().record_planner_task()
            return self.queue.pop(0)
        return None

    def log_task_result(self, task: str, actions: List[str]):
        """Store the outcome of an executed step for reflection."""
        self.task_history.append({"task": task, "actions": actions})

    def generate_reflection(self) -> str:
        """Called when queue is empty to reflect on the completed goal."""
        if not self.current_goal or not self.task_history:
            return ""

        context = f"GOAL: {self.current_goal}\n\nEXECUTION LOG:\n"
        for entry in self.task_history:
            context += f"- STEP: {entry['task']}\n"
            for action in entry['actions']:
                context += f"  > {action}\n"

        prompt = [
            {"role": "system", "content": REFLECTION_PROMPT},
            {"role": "user", "content": context}
        ]

        try:
            result, _ = self.router.generate(prompt, task_type="Thought")
            reflection = self._extract_content(result.output).strip()
            
            # Save strategy
            self.strategies.append({
                "goal": self.current_goal,
                "strategy_note": reflection
            })
            self._save_strategies()
            StatsManager().record_reflection()
            
            self.current_goal = None
            self.task_history = []
            return reflection
        except Exception as e:
            logger.error(f"Reflection failed: {e}")
            return ""

    def get_strategy_context(self) -> str:
        """Returns the last 5 reflection strategies to inject into prompt."""
        if not self.strategies:
            return ""
        
        recent = self.strategies[-5:]
        ctx = "YOUR PREVIOUS STRATEGIC REFLECTIONS:\n"
        for s in recent:
            ctx += f"- When tackling: '{s['goal']}', you learned: {s['strategy_note']}\n"
        return ctx
