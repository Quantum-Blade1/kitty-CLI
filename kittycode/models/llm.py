from kittycode.models.router import ModelRouter
from kittycode.utils.helpers import extract_content


class LLMClient:
    def __init__(self, memory_manager, engine):
        self.memory = memory_manager
        self.engine = engine
        self.router = ModelRouter()

    def get_thought(self):
        user_name = self.memory.get("user_name", "Friend")
        try:
            prompt = [
                {"role": "system", "content": f"You are Kitty. Give {user_name} one tiny, sweet, 1-sentence thought. Plain text only."},
                {"role": "user", "content": "Share a single warm thought."}
            ]
            result, model_key = self.router.generate(prompt, task_type="Thought")
            return extract_content(result.output).strip()
        except Exception as e:
            return f"Thinking of you always! nya~ ♥ ({str(e)})"

    def get_response(self, user_input: str, history: list, current_mode: str = "Chat", status=None):
        user_name = self.memory.get("user_name", "Friend")
        
        # Retrieve semantically relevant memories
        try:
            relevant_memories = self.memory.get_relevant_context(user_input, k=5)
            mem_ctx = "\n".join([f"- {m}" for m in relevant_memories]) if relevant_memories else "No specific memory triggered."
        except Exception:
            # Fallback for when ML dependencies aren't loaded or crash
            mem_ctx = "Memory system unavailable."
            
        full_input = f"[USER_NAME: {user_name}]\n[RELEVANT MEMORIES]\n{mem_ctx}\n\n[USER: {user_input}]"
        
        history.append({"role": "user", "content": full_input})
        
        try:
            result, model_key = self.router.generate(history, task_type=current_mode)
            raw_text = extract_content(result.output)
            
            # Use ToolEngine to process JSON actions
            tool_logs, clean_speech = self.engine.execute_tools(raw_text, status=status)
            
            actions_taken = [f"Routed via: {model_key}"] + tool_logs
            
            history.append({"role": "assistant", "content": clean_speech})
            return (clean_speech, actions_taken, history)
        except Exception as e:
            from kittycode.config.settings import RuntimeConfig
            if RuntimeConfig().persona_enabled:
                return (f"Oh no! Kitty had a little tumble: {str(e)}... nya~", [], history)
            else:
                return (f"Error: {str(e)}", [], history)
