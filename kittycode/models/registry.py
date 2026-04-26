# registry.py
from typing import Dict, List, TypedDict

class ModelConfig(TypedDict):
    id: str
    provider: str
    strengths: List[str]
    max_tokens: int

# Configuration for available models
MODEL_REGISTRY: Dict[str, ModelConfig] = {
    # Primary Models
    "gpt-4o": {
        "id": "openai/gpt-4o",
        "provider": "openai",
        "strengths": ["code", "reasoning", "chat", "stable", "general"],
        "max_tokens": 1000  # Budget cap
    },
    "gpt-4o-mini": {
        "id": "openai/gpt-4o-mini",
        "provider": "openai",
        "strengths": ["chat", "speed", "general"],
        "max_tokens": 4096
    },
    "deepseek-v3": {
        "id": "deepseek/deepseek-chat",
        "provider": "deepseek",
        "strengths": ["chat", "speed", "general"],
        "max_tokens": 4096
    },
    "deepseek-r1": {
        "id": "deepseek/deepseek-r1",
        "provider": "deepseek",
        "strengths": ["code", "reasoning", "complex"],
        "max_tokens": 1000 # Budget cap
    },
    "llama-3.2": {
        "id": "meta-llama/llama-3.2-3b-instruct", 
        "provider": "meta",
        "strengths": ["chat", "creative", "general"],
        "max_tokens": 4096
    },
    
    "qwen-coder": {
        "id": "qwen/qwen-2.5-coder-32b-instruct",
        "provider": "openrouter",
        "strengths": ["code", "speed", "logic"],
        "max_tokens": 1000 # Budget cap
    },
    # Fallback Models
    "claude-sonnet": {
        "id": "anthropic/claude-3.7-sonnet",
        "provider": "anthropic",
        "strengths": ["code", "reasoning", "complex", "chat"],
        "max_tokens": 800 # Extreme budget cap
    },

    "claude-haiku": {
        "id": "anthropic/claude-3.5-haiku",
        "provider": "anthropic",
        "strengths": ["speed", "chat", "general"],
        "max_tokens": 1000
    },
    "gemini-2.0": {
        "id": "google/gemini-2.0-flash-001",
        "provider": "google",
        "strengths": ["reasoning", "context", "speed"],
        "max_tokens": 4096
    }
}

# Task-to-Model mapping strategies
DEFAULT_TASK_PREFERENCES = {
    "Code": {
        "primary": ["qwen-coder", "deepseek-r1", "gpt-4o"],
        "fallback": ["claude-sonnet", "gemini-2.0", "claude-haiku", "gpt-4o-mini"]
    },
    "Chat": {
        "primary": ["gpt-4o", "deepseek-v3"],
        "fallback": ["qwen-coder", "llama-3.2", "claude-haiku", "gemini-2.0", "gpt-4o-mini"]
    },
    "Thought": {
        "primary": ["deepseek-r1", "gpt-4o"],
        "fallback": ["qwen-coder", "claude-sonnet", "gemini-2.0", "claude-haiku"]
    }
}



# Mutable runtime preferences (copied from defaults on boot/reset)
TASK_PREFERENCES = {
    task: {"primary": cfg["primary"][:], "fallback": cfg["fallback"][:]}
    for task, cfg in DEFAULT_TASK_PREFERENCES.items()
}
