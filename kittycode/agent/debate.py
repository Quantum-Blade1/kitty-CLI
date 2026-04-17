import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

CRITIC_PROMPT = """
You are the Critic — an internal quality gate for an AI code assistant.
You are reviewing the Builder's output for a specific subtask.
Evaluate the output for:
1. Correctness — does it actually accomplish the task?
2. Safety — are there unsafe file operations or path traversal risks?
3. Logical flaws — missing edge cases, wrong assumptions?

Respond with EXACTLY one of:
PASS: <one sentence explaining why it's acceptable>
REVISE: <one sentence explaining the specific issue to fix>

Do not output anything else.
"""

BUILDER_REVISION_PROMPT = """
The Critic found an issue with your previous output.
Revise your response to fix the following:
{critique}

Original task: {task}
Your previous output: {previous_output}

Provide a corrected response.
IMPORTANT: You MUST briefly narrate what you are doing (e.g. "I am creating the folder..." or "I am writing the server file...") BEFORE outputting any tool JSON arrays.
"""

class DebateManager:
    """Orchestrates Builder → Critic → (optional revision) debate loop."""
    
    def __init__(self, router, engine):
        self.router = router
        self.engine = engine

    def _extract_content(self, output):
        if isinstance(output, list) and len(output) > 0: output = output[-1]
        if isinstance(output, dict): return output.get("content", str(output))
        return str(output)

    def _critic_review(self, task: str, builder_output: str) -> Tuple[bool, str]:
        """
        Sends Builder output to Critic for review.
        Returns (passed: bool, critique_text: str)
        """
        review_input = f"TASK: {task}\n\nBUILDER OUTPUT:\n{builder_output}"
        
        prompt = [
            {"role": "system", "content": CRITIC_PROMPT},
            {"role": "user", "content": review_input}
        ]
        
        try:
            result, _ = self.router.generate(prompt, task_type="Thought")
            verdict = self._extract_content(result.output).strip()
            
            if verdict.upper().startswith("PASS"):
                return True, verdict
            elif verdict.upper().startswith("REVISE"):
                return False, verdict.replace("REVISE:", "").strip()
            else:
                # If critic output is malformed, pass by default to avoid wasted calls
                logger.warning(f"Critic gave malformed verdict: {verdict}")
                return True, verdict
        except Exception as e:
            logger.error(f"Critic review failed: {e}")
            # On error, pass by default — don't block execution
            return True, f"Critic unavailable: {e}"

    def _builder_revise(self, task: str, previous_output: str, critique: str, history: list, status=None) -> Tuple[str, List[str]]:
        """Ask Builder to revise its output based on Critic feedback."""
        revision_prompt = BUILDER_REVISION_PROMPT.format(
            critique=critique,
            task=task,
            previous_output=previous_output[:500]  # Truncate to save tokens
        )
        
        history_copy = history.copy()
        history_copy.append({"role": "user", "content": revision_prompt})
        
        try:
            result, model_key = self.router.generate(history_copy, task_type="Code")
            raw_text = self._extract_content(result.output)
            
            # Process tools from revised output
            tool_logs, clean_speech = self.engine.execute_tools(raw_text, status=status)
            actions = [f"Revised via: {model_key}"] + tool_logs
            
            return clean_speech, actions
        except Exception as e:
            logger.error(f"Builder revision failed: {e}")
            return f"Revision failed: {e}", []

    def run_step(self, task: str, history: list, status=None) -> Tuple[str, List[str], list]:
        """
        Full debate cycle for a single step:
        1. Builder generates initial output
        2. Critic reviews
        3. If REVISE, Builder gets one retry
        4. Returns final (output, actions, updated_history)
        """
        # Step 1: Builder generates
        is_executable = True
        task_str = str(task)
        if isinstance(task, dict):
            task_str = task.get("step", str(task))
            is_executable = task.get("executable", False)
            
        if is_executable:
            builder_input = f"[AUTONOMOUS STEP] Execute this specific step using tools: {task_str}\nIMPORTANT: Briefly narrate what you are about to do (e.g. 'I will now scaffold the folder structure...') BEFORE outputting the tool JSON array."
        else:
            builder_input = f"[REASONING STEP] Process this specific step. DO NOT use structural tools (write/mkdir/run_cmd): {task_str}"
            
        history_copy = history.copy()
        history_copy.append({"role": "user", "content": builder_input})
        
        try:
            result, model_key = self.router.generate(history_copy, task_type="Code")
            raw_text = self._extract_content(result.output)
            tool_logs, clean_speech = self.engine.execute_tools(raw_text, status=status)
            actions = [f"Builder via: {model_key}"] + tool_logs
        except Exception as e:
            return f"Builder failed: {e}", [], history
        
        # Step 2: Critic reviews
        passed, critique = self._critic_review(task, clean_speech)
        actions.append(f"Critic: {'PASS' if passed else 'REVISE'}")
        
        # Step 3: If Critic rejected, Builder gets ONE revision
        if not passed:
            actions.append(f"Revision requested: {critique}")
            revised_speech, revised_actions = self._builder_revise(task, clean_speech, critique, history_copy, status=status)
            clean_speech = revised_speech
            actions.extend(revised_actions)
        
        # Update history with final output
        history_copy.append({"role": "assistant", "content": clean_speech})
        
        return clean_speech, actions, history_copy
