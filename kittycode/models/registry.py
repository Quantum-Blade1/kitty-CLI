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
    "gpt-4.1": {
        "id": "openai/gpt-4.1",
        "provider": "openai",
        "strengths": ["code", "reasoning", "chat", "stable", "general"],
        "max_tokens": 8192
    },
    "deepseek-v3": {
        "id": "deepseek/deepseek-chat",
        "provider": "deepseek",
        "strengths": ["chat", "speed", "general"],
        "max_tokens": 4096
    },
    "deepseek-r1": {
        "id": "deepseek/deepseek-reasoner",
        "provider": "deepseek",
        "strengths": ["code", "reasoning", "complex"],
        "max_tokens": 8192
    },
    "llama-4": {
        "id": "meta/llama-4", 
        "provider": "meta",
        "strengths": ["chat", "creative", "general"],
        "max_tokens": 4096
    },
    
    # Fallback Models
    "claude-sonnet": {
        "id": "anthropic/claude-sonnet-4-5",
        "provider": "anthropic",
        "strengths": ["code", "reasoning", "complex", "chat"],
        "max_tokens": 8192
    },
    "claude-haiku": {
        "id": "anthropic/claude-haiku-4-5",
        "provider": "anthropic",
        "strengths": ["speed", "chat", "general"],
        "max_tokens": 4096
    },
    "gemini-pro": {
        "id": "google/gemini-2.5-pro",
        "provider": "google",
        "strengths": ["reasoning", "context", "multimodal"],
        "max_tokens": 8192
    },
    "bytez-llama": {
        "id": "meta-llama/Meta-Llama-3-8B-Instruct",
        "provider": "bytez",
        "strengths": ["chat", "speed", "general"],
        "max_tokens": 8192
    },
    "bytez-qwen-coder": {
        "id": "Qwen/Qwen2.5-Coder-32B-Instruct",
        "provider": "bytez",
        "strengths": ["code", "speed", "reasoning"],
        "max_tokens": 8192
    }
}

# Task-to-Model mapping strategies
DEFAULT_TASK_PREFERENCES = {
    "Code": {
        "primary": ["bytez-qwen-coder", "gpt-4.1"],
        "fallback": ["claude-sonnet", "claude-haiku", "gemini-pro", "bytez-llama"]
    },
    "Chat": {
        "primary": ["gpt-4.1"],
        "fallback": ["claude-sonnet", "claude-haiku", "gemini-pro", "bytez-llama"]
    },
    "Thought": {
        "primary": ["gpt-4.1"],
        "fallback": ["claude-sonnet", "claude-haiku", "gemini-pro", "bytez-llama"]
    }
}

# Mutable runtime preferences (copied from defaults on boot/reset)
TASK_PREFERENCES = {
    task: {"primary": cfg["primary"][:], "fallback": cfg["fallback"][:]}
    for task, cfg in DEFAULT_TASK_PREFERENCES.items()
}
