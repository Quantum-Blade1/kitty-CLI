from typing import Callable, Dict, Any

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, description: str, parameters: Dict[str, Any], func: Callable, destructive: bool = False):
        """
        Registers a tool for the engine.
        :param destructive: If True, the engine will prompt the user before execution.
        """
        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "func": func,
            "destructive": destructive
        }

    def get_tool(self, name: str) -> Dict[str, Any]:
        return self._tools.get(name)

    def get_all_schemas(self):
        """Returns JSON schema definitions of all registered tools for the LLM."""
        return [
            {
                "name": key,
                "description": val["description"],
                "parameters": val["parameters"]
            }
            for key, val in self._tools.items()
        ]
