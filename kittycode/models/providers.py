from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from bytez import Bytez as _Bytez
except ImportError:  # pragma: no cover — optional runtime dep
    _Bytez = None  # type: ignore


@dataclass
class ProviderResult:
    """Unified result object for all providers."""
    output: Any
    error: Optional[str] = None


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
        
        # Format prompt if it's a list (chat history)
        if isinstance(prompt, list):
            # Basic chat template for Bytez/HF models
            lines = []
            for msg in prompt:
                role = msg.get("role", "user").upper()
                content = msg.get("content", "")
                lines.append(f"{role}: {content}")
            real_prompt = "\n".join(lines) + "\nASSISTANT:"
        else:
            real_prompt = str(prompt)

        return model.run(real_prompt, params=params or {})

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

        # Build structured contents for multi-turn context
        if isinstance(prompt, list):
            contents = []
            for msg in prompt:
                role = msg.get("role", "user")
                # Gemini uses "user" / "model"; map "assistant" -> "model"
                gemini_role = "model" if role == "assistant" else "user"
                contents.append(types.Content(
                    role=gemini_role,
                    parts=[types.Part(text=msg.get("content", ""))]
                ))
        else:
            contents = str(prompt)

        temperature = params.get("temperature", 0.7) if params else 0.7
        real_model_id = model_id.split("/")[-1] if "/" in model_id else model_id

        try:
            response = self.client.models.generate_content(
                model=real_model_id,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=params.get("temperature", 0.7) if params else 0.7,
                    max_output_tokens=params.get("max_tokens") if params else None
                )
            )

        except Exception as e:
            raise RuntimeError(f"Gemini API call failed: {e}")

        # Guard against None response text (can happen with safety filters)
        text = response.text if response.text else ""
        return ProviderResult(output=text)

class OpenRouterProvider(BaseProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def has_client(self) -> bool:
        return bool(self.api_key)

    def run(self, model_id: str, prompt: Any, params: Optional[Dict] = None) -> Any:
        if not self.has_client():
            raise RuntimeError("OpenRouter Provider client not initialized.")
        import urllib.request
        import urllib.error
        import json

        contents = []
        if isinstance(prompt, list):
            for msg in prompt:
                role = msg.get("role", "user")
                text = str(msg.get("content", ""))
                if text:
                    contents.append({"role": role, "content": text})
        else:
            prompt_str = str(prompt).strip()
            if prompt_str:
                contents.append({"role": "user", "content": prompt_str})

        if not contents:
            return ProviderResult(output="", error="Empty prompt")

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        temperature = params.get("temperature", 0.7) if params else 0.7
        max_tokens = params.get("max_tokens") if params else None
        
        data = {
            "model": model_id,
            "messages": contents,
            "temperature": temperature
        }
        if max_tokens:
            data["max_tokens"] = max_tokens


        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=30) as response:  # nosec B310
                result = json.loads(response.read().decode("utf-8"))
                # Safely extract the response text
                try:
                    text = result["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError):
                    error_detail = result.get("error", {})
                    if isinstance(error_detail, dict):
                        error_msg = error_detail.get("message", str(result))
                    else:
                        error_msg = str(error_detail) if error_detail else str(result)
                    return ProviderResult(output="", error=f"Unexpected response structure: {error_msg}")
                return ProviderResult(output=text)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            raise Exception(f"OpenRouter HTTP {e.code}: {error_body[:300]}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"OpenRouter connection error: {e.reason}")
        except Exception as e:
            raise RuntimeError(f"OpenRouter API error: {str(e)}")
