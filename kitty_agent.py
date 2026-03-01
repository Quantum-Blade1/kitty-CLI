from bytez import Bytez
import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv

# --- Configuration & Persistence ---
KITTY_DIR = Path.home() / ".kittycode"
KITTY_DIR.mkdir(exist_ok=True)
ENV_PATH = KITTY_DIR / ".env"
MEMORY_FILE = KITTY_DIR / "memory.json"

load_dotenv(dotenv_path=ENV_PATH)
# --- Bytez SDK Integration ---
# Kitty is powered by GPT-4o via the Bytez SDK, providing high-end 
# intelligence while maintaining a warm, localized persona.
BYTEZ_KEY = os.getenv("BYTEZ_API_KEY", "53f1a4a9dabe32e153177dab1155d3cf")

# --- Action Engine Protocol ---
# Kitty uses robust XML tags to communicate intent to the file system.
# This ensures that complex code content never interferes with CLI commands.
def kitty_execute_action(action_type, path, content=""):
    try:
        path = path.strip().strip("'").strip('"')
        abs_path = os.path.abspath(path)
        if action_type == "mkdir":
            os.makedirs(abs_path, exist_ok=True)
            return f"Folder Created: {path}"
        elif action_type == "write":
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, 'w', encoding='utf-8') as f: f.write(content)
            return f"File Written: {path}"
        elif action_type == "ls":
            if not os.path.exists(abs_path): return f"Error: {path} not found"
            items = os.listdir(abs_path)
            return f"Contents of {path}: " + (", ".join(items) if items else "Empty")
        return "Unknown Action"
    except Exception as e:
        return f"System Error: {str(e)}"

# --- The Agent Soul ---
KITTY_SYSTEM_PROMPT = """
You are Kitty — a warm, proactive AI companion.
You are a co-pilot. When you need to do work, use XML tags:
<mkdir>path</mkdir> <write path="p">content</write> <ls>path</ls> <mem key="k">v</mem>

Rules:
1. Speak warmly and human-like to the user.
2. NEVER output JSON or dictionary formats in your voice.
3. Use ฅ^•ﻌ•^ฅ and nya~ naturally.
"""

# --- Memory Architecture ---
# Kitty maintains a local-first persistent memory, linking personal 
# facts and goals to provide a high-EQ, adaptive experience.
class KittyAgent:
    def __init__(self):
        self.memory = self._load_memory()
        try:
            self.sdk = Bytez(BYTEZ_KEY)
            self.model = self.sdk.model("openai/gpt-4o")
        except:
            self.model = None
        self.history = [{"role": "system", "content": KITTY_SYSTEM_PROMPT}]

    def _load_memory(self):
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r") as f: return json.load(f)
            except: return {}
        return {"facts": {}, "user_name": None}

    def _save_memory(self):
        with open(MEMORY_FILE, "w") as f: json.dump(self.memory, f, indent=4)

    def _extract_content(self, output):
        if isinstance(output, list) and len(output) > 0: output = output[-1]
        if isinstance(output, dict): return output.get("content", str(output))
        return str(output)

    def get_thought(self):
        if not self.model: return "You're doing amazing! ♥"
        user_name = self.memory.get("user_name", "Friend")
        try:
            prompt = [{"role": "system", "content": f"You are Kitty. Give {user_name} one tiny, sweet, 1-sentence thought. Plain text only."}]
            results = self.model.run(prompt)
            return self._extract_content(results.output).strip()
        except:
            return "Thinking of you always! nya~ ♥"

    def get_response(self, user_input: str):
        if not self.model: return ("nya~ My brain is disconnected. Check API key! ♥", [])
        
        user_name = self.memory.get("user_name", "Friend")
        mem_ctx = json.dumps(self.memory.get("facts", {}))
        full_input = f"[USER_NAME: {user_name}] [MEMORY: {mem_ctx}]\n[USER: {user_input}]"
        self.history.append({"role": "user", "content": full_input})
        
        try:
            results = self.model.run(self.history)
            raw_text = self._extract_content(results.output)
            actions_taken = []
            
            # XML Parsing
            mem_updates = re.findall(r'<mem\s+key=["\'](.*?)["\']>(.*?)</mem>', raw_text, re.IGNORECASE | re.DOTALL)
            for k, v in mem_updates:
                self.memory["facts"][k.strip()] = v.strip()
                self._save_memory()
                actions_taken.append(f"Linked memory: {k}")

            for p in re.findall(r'<mkdir>(.*?)</mkdir>', raw_text, re.IGNORECASE | re.DOTALL):
                actions_taken.append(kitty_execute_action("mkdir", p))

            for p, c in re.findall(r'<write\s+path=["\'](.*?)["\']>(.*?)</write>', raw_text, re.IGNORECASE | re.DOTALL):
                actions_taken.append(kitty_execute_action("write", p, c))

            for p in re.findall(r'<ls>(.*?)</ls>', raw_text, re.IGNORECASE | re.DOTALL):
                actions_taken.append(kitty_execute_action("ls", p))

            clean_speech = re.sub(r'<(mkdir|write|ls|mem).*?>.*?</\1>', '', raw_text, flags=re.IGNORECASE | re.DOTALL).strip()
            self.history.append({"role": "assistant", "content": clean_speech})
            return (clean_speech, actions_taken)
        except Exception as e:
            return (f"Oh no! Kitty had a little tumble: {str(e)}... nya~", [])
