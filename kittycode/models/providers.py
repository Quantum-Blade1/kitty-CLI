from typing import Any, Dict, Optional

try:
    from bytez import Bytez as _Bytez
except ImportError:  # pragma: no cover — optional runtime dep
    _Bytez = None  # type: ignore


class BaseProvider:
    def run(self, model_id: str, prompt: Any, params: Optional[Dict] = None) -> Any:
        raise NotImplementedError


class BytezProvider(BaseProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.sdk = _Bytez(api_key) if (api_key and _Bytez is not None) else None
        self._instances: Dict[str, Any] = {}

    def has_client(self) -> bool:
        return self.sdk is not None

    def _get_model(self, model_id: str):
        if not self.sdk:
            return None
        if model_id not in self._instances:
            self._instances[model_id] = self.sdk.model(model_id)
        return self._instances[model_id]

    def run(self, model_id: str, prompt: Any, params: Optional[Dict] = None) -> Any:
        model = self._get_model(model_id)
        if model is None:
            raise RuntimeError("Provider client not initialized.")
        return model.run(prompt, params=params or {})

class GeminiProvider(BaseProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        try:
            from google import genai
            self.client = genai.Client(api_key=api_key) if api_key else None
        except ImportError:
            self.client = None

    def has_client(self) -> bool:
        return self.client is not None

    def run(self, model_id: str, prompt: Any, params: Optional[Dict] = None) -> Any:
        if not self.client:
            raise RuntimeError("Gemini Provider client not initialized.")
        from google.genai import types
        
        contents = ""
        if isinstance(prompt, list):
            for msg in prompt:
                role = msg.get("role", "user").upper()
                contents += f"[{role}]\n{msg.get('content', '')}\n\n"
        else:
            contents = str(prompt)

        temperature = params.get("temperature", 0.7) if params else 0.7
        real_model_id = model_id.split("/")[-1] if "/" in model_id else model_id
        
        response = self.client.models.generate_content(
            model=real_model_id,
            contents=contents,
            config=types.GenerateContentConfig(temperature=temperature)
        )
        
        class MockResult:
            def __init__(self, text):
                self.output = text
                self.error = None
        
        return MockResult(response.text)

class OpenRouterProvider(BaseProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def has_client(self) -> bool:
        return bool(self.api_key)

    def run(self, model_id: str, prompt: Any, params: Optional[Dict] = None) -> Any:
        if not self.has_client():
            raise RuntimeError("OpenRouter Provider client not initialized.")
        import urllib.request
        import json

        contents = []
        if isinstance(prompt, list):
            for msg in prompt:
                role = msg.get("role", "user")
                contents.append({"role": role, "content": str(msg.get("content", ""))})
        else:
            contents.append({"role": "user", "content": str(prompt)})

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        temperature = params.get("temperature", 0.7) if params else 0.7
        data = {
            "model": model_id,
            "messages": contents,
            "temperature": temperature
        }
        
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
        
        class MockResult:
            def __init__(self, text):
                self.output = text
                self.error = None
                
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode("utf-8"))
                text = result["choices"][0]["message"]["content"]
                return MockResult(text)
        except Exception as e:
            raise Exception(f"OpenRouter API error: {str(e)}")
