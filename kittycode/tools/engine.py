import logging
import yaml
from rich.prompt import Confirm
from typing import List, Tuple
from kittycode.utils.stats import StatsManager
from kittycode.telemetry.logger import get_logger

log = get_logger("tools.engine")
logger = logging.getLogger(__name__)  # Keep for backward compat

class ToolEngine:
    def __init__(self, registry):
        self.registry = registry
        self._critic = None  # Lazy init to avoid circular imports

    @property
    def critic(self):
        if self._critic is None:
            from kittycode.core.critic import SafetyCritic
            self._critic = SafetyCritic()
        return self._critic

    def _resolve_safe_path(self, target_path: str) -> str:
        """
        Resolves and validates a path within the project sandbox.
        Delegates to the centralized SandboxValidator for all security checks.
        """
        from kittycode.security.sandbox import get_validator, SandboxError
        try:
            return get_validator().resolve_safe(target_path)
        except SandboxError as e:
            raise PermissionError(str(e))

    def execute_tools(self, json_string: str, status=None) -> Tuple[List[str], str]:
        """
        Parses JSON tool array strings and executes them.
        Flow: Parse → Critic Review → Path Resolution → Confirmation → Execute
        """
        actions_taken = []
        
        import re
        
        clean_speech = json_string.strip()
        tools_to_run = []
        
        # Strip out code block ticks if they exist
        target_str = json_string
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', json_string, re.DOTALL)
        if json_match:
            target_str = json_match.group(1)
            
        start_idx = target_str.find('[')
        end_idx = target_str.rfind(']')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = target_str[start_idx:end_idx+1]
            
            # Pre-processing heuristics for LLM hallucinations
            # 1. Escaping raw Windows paths (C:\foo -> C:\\foo)
            json_str = re.sub(r'\\([^"\\/bfnrtu])', r'\\\\\1', json_str)
            
            # 2. Aggressively sanitize unescaped inner quotes inside the "command" value.
            # Captures "command": " ... " and escapes any unescaped quotes inside.
            def escape_inner_quotes(match):
                prefix = match.group(1) # "command": "
                cmd_content = match.group(2) # inner content
                suffix = match.group(3) # "
                # Escape any unescaped quotes inside the content
                escaped_content = re.sub(r'(?<!\\)"', r'\"', cmd_content)
                return f"{prefix}{escaped_content}{suffix}"
            
            json_str = re.sub(r'("command"\s*:\s*")(.*?)("\s*\}|"\s*,)', escape_inner_quotes, json_str, flags=re.DOTALL)

            
            try:
                # YAML is a superset of JSON and far more resilient to raw LLM output escaping errors
                tools_to_run = yaml.safe_load(json_str)
                # Strip the first occurrence of the JSON block from the speech
                clean_speech = re.sub(re.escape(json_str), "", json_string, count=1)
                clean_speech = re.sub(r"```json|```", "", clean_speech).strip()
                if not isinstance(tools_to_run, list):
                    tools_to_run = [tools_to_run] if tools_to_run else []
            except Exception as e:
                logger.warning(f"Failed to decode JSON tools from output via YAML: {e}")
                actions_taken.append("Tool execution skipped: Malformed tool payload.")
                tools_to_run = []
        
        for tool_call in tools_to_run:
            if not isinstance(tool_call, dict) or "tool" not in tool_call:
                continue
                
            tool_name = tool_call["tool"]
            args = tool_call.get("args", {})
            
            tool_def = self.registry.get_tool(tool_name)
            if not tool_def:
                actions_taken.append(f"Error: Unknown tool '{tool_name}' requested.")
                continue

            # === SAFETY CRITIC GATE (pre-execution) ===
            verdict = self.critic.review(tool_name, args)
            if not verdict.allowed:
                actions_taken.append(f"Critic BLOCKED '{tool_name}': {verdict.reason}")
                logger.warning(f"SafetyCritic blocked {tool_name}: {verdict.reason}")
                continue
                
            # Resolve safe path
            if "path" in args:
                try:
                    args["path"] = self._resolve_safe_path(args["path"])
                except PermissionError as e:
                    actions_taken.append(f"Permission Denied: {e}")
                    continue

            # Destructive confirmation
            if tool_def["destructive"]:
                from kittycode.cli.ui import console
                
                # Special handling for 'write' to show a diff
                showed_diff = False
                if tool_name == "write" and "path" in args:
                    target_path = args["path"]
                    new_content = args.get("content", "")
                    if os.path.exists(target_path):
                        try:
                            with open(target_path, 'r', encoding='utf-8') as f:
                                old_content = f.read()
                            
                            from kittycode.utils.diff import generate_unified_diff, render_diff_panel
                            diff_text = generate_unified_diff(target_path, old_content, new_content)
                            if diff_text != "[no changes]":
                                panel = render_diff_panel(target_path, diff_text)
                                console.print(panel)
                                showed_diff = True
                        except Exception as e:
                            logger.warning(f"Failed to generate diff for {target_path}: {e}")

                if not showed_diff:
                    confirm_msg = f"\n[bold red]⚠️  Kitty wants to {tool_name}![/bold red]\n[yellow]Arguments: {args}[/yellow]\nDo you want to allow this?"
                else:
                    confirm_msg = f"\n[bold red]⚠️  Apply these changes?[/bold red]"
                
                # Use the explicitly passed status object, or fallback to inspecting the console
                active_status = status if status else (hasattr(console, "_status") and console._status)
                if active_status:
                    active_status.stop()
                    
                is_allowed = Confirm.ask(confirm_msg, default=False)
                
                # Resume status spinner if it was running
                if active_status:
                    active_status.start()
                    
                if not is_allowed:
                    actions_taken.append(f"Blocked: User denied {tool_name}")
                    continue
                    
            # Execution
            try:
                result = tool_def["func"](**args)
                actions_taken.append(result)
                StatsManager().record_tool_exec()
            except Exception as e:
                actions_taken.append(f"Error executing {tool_name}: {e}")
                
        return actions_taken, clean_speech
