"""Model inference service with pluggable provider backends.

Supports Ollama, vLLM, and HuggingFace Inference Endpoints.
The provider is selected via the BRIDGE_INFERENCE_PROVIDER environment variable.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

import httpx

from api.config import settings

logger = logging.getLogger(__name__)

ALPACA_TEMPLATE = (
    "Below is an instruction that describes a task. "
    "Write a response that appropriately completes the request.\n\n"
    "### Instruction:\n{instruction}\n\n### Response:\n"
)


def format_alpaca_prompt(instruction: str, context: str = "") -> str:
    """Format an instruction into Alpaca prompt format.

    Args:
        instruction: The user's instruction/question.
        context: Optional context to include.

    Returns:
        Formatted prompt string.
    """
    if context:
        return (
            "Below is an instruction that describes a task, paired with further context. "
            "Write a response that appropriately completes the request.\n\n"
            f"### Instruction:\n{instruction}\n\n### Input:\n{context}\n\n### Response:\n"
        )
    return ALPACA_TEMPLATE.format(instruction=instruction)


def format_chat_messages(messages: list[dict]) -> str:
    """Convert chat messages into a single Alpaca-formatted prompt.

    Args:
        messages: List of message dicts with 'role' and 'content' keys.

    Returns:
        Formatted prompt string combining all messages.
    """
    parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            parts.append(f"System: {content}")
        elif role == "user":
            parts.append(f"User: {content}")
        elif role == "assistant":
            parts.append(f"Assistant: {content}")
    combined = "\n".join(parts)
    return format_alpaca_prompt(combined)


class InferenceProvider(ABC):
    """Abstract base class for model inference providers."""

    @abstractmethod
    async def generate(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.1) -> str:
        """Generate a completion for the given prompt.

        Args:
            prompt: The formatted prompt string.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.

        Returns:
            Generated text string.
        """

    @abstractmethod
    async def generate_stream(
        self, prompt: str, max_tokens: int = 2048, temperature: float = 0.1
    ) -> AsyncGenerator[str, None]:
        """Stream a completion token-by-token.

        Args:
            prompt: The formatted prompt string.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.

        Yields:
            Individual tokens as they are generated.
        """

    async def chat(self, messages: list[dict], max_tokens: int = 2048, temperature: float = 0.1) -> str:
        """Generate a chat response from conversation messages.

        Default falls back to generate with formatted prompt.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.

        Returns:
            Generated response text.
        """
        return await self.generate(format_chat_messages(messages), max_tokens, temperature)

    async def chat_stream(
        self, messages: list[dict], max_tokens: int = 2048, temperature: float = 0.1
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response token-by-token.

        Default falls back to generate_stream with formatted prompt.
        """
        async for token in self.generate_stream(format_chat_messages(messages), max_tokens, temperature):
            yield token

    @abstractmethod
    async def list_models(self) -> list[dict]:
        """List available models from this provider.

        Returns:
            List of model info dicts with at minimum an 'id' key.
        """


class OllamaProvider(InferenceProvider):
    """Inference provider using a local Ollama server."""

    def __init__(self, base_url: str, model_name: str):
        """Initialize Ollama provider.

        Args:
            base_url: Ollama server URL (e.g. http://localhost:11434).
            model_name: Model name/tag to use.
        """
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    async def generate(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.1) -> str:
        """Generate a completion via Ollama API."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens, "temperature": temperature},
                },
            )
            response.raise_for_status()
            return response.json()["response"]

    async def generate_stream(
        self, prompt: str, max_tokens: int = 2048, temperature: float = 0.1
    ) -> AsyncGenerator[str, None]:
        """Stream a completion via Ollama API."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": True,
                    "options": {"num_predict": max_tokens, "temperature": temperature},
                },
            ) as response:
                response.raise_for_status()
                import json as json_mod

                async for line in response.aiter_lines():
                    if line.strip():
                        data = json_mod.loads(line)
                        if "response" in data:
                            yield data["response"]

    async def chat(self, messages: list[dict], max_tokens: int = 2048, temperature: float = 0.1) -> str:
        """Generate a chat response via Ollama's native chat API."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "stream": False,
                    "options": {"num_predict": max_tokens, "temperature": temperature},
                },
            )
            response.raise_for_status()
            return response.json()["message"]["content"]

    async def chat_stream(
        self, messages: list[dict], max_tokens: int = 2048, temperature: float = 0.1
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response via Ollama's native chat API."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "stream": True,
                    "options": {"num_predict": max_tokens, "temperature": temperature},
                },
            ) as response:
                response.raise_for_status()
                import json as json_mod

                async for line in response.aiter_lines():
                    if line.strip():
                        data = json_mod.loads(line)
                        if "message" in data and data["message"].get("content"):
                            yield data["message"]["content"]

    async def list_models(self) -> list[dict]:
        """List models available in Ollama."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
            return [{"id": m["name"], "provider": "ollama"} for m in models]


class VllmProvider(InferenceProvider):
    """Inference provider using a vLLM OpenAI-compatible server."""

    def __init__(self, base_url: str, model_name: str):
        """Initialize vLLM provider.

        Args:
            base_url: vLLM server URL.
            model_name: Model name served by vLLM.
        """
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    async def generate(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.1) -> str:
        """Generate a completion via vLLM OpenAI-compatible API."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/completions",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": False,
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["text"]

    async def generate_stream(
        self, prompt: str, max_tokens: int = 2048, temperature: float = 0.1
    ) -> AsyncGenerator[str, None]:
        """Stream a completion via vLLM OpenAI-compatible API."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/completions",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                import json as json_mod

                async for line in response.aiter_lines():
                    line = line.strip()
                    if line.startswith("data: ") and line != "data: [DONE]":
                        data = json_mod.loads(line[6:])
                        text = data.get("choices", [{}])[0].get("text", "")
                        if text:
                            yield text

    async def list_models(self) -> list[dict]:
        """List models available from vLLM server."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/v1/models")
            response.raise_for_status()
            models = response.json().get("data", [])
            return [{"id": m["id"], "provider": "vllm"} for m in models]


class HuggingFaceProvider(InferenceProvider):
    """Inference provider using HuggingFace Inference Endpoints."""

    def __init__(self, inference_url: str, api_token: str, model_name: str):
        """Initialize HuggingFace provider.

        Args:
            inference_url: HF Inference Endpoint URL.
            api_token: HuggingFace API token.
            model_name: Model identifier on HuggingFace.
        """
        self.inference_url = inference_url.rstrip("/")
        self.api_token = api_token
        self.model_name = model_name

    def _headers(self) -> dict:
        """Build authorization headers."""
        return {"Authorization": f"Bearer {self.api_token}"}

    async def generate(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.1) -> str:
        """Generate a completion via HuggingFace Inference API."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                self.inference_url,
                headers=self._headers(),
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": max_tokens,
                        "temperature": temperature,
                        "return_full_text": False,
                    },
                },
            )
            response.raise_for_status()
            result = response.json()
            if isinstance(result, list):
                return result[0].get("generated_text", "")
            return result.get("generated_text", "")

    async def generate_stream(
        self, prompt: str, max_tokens: int = 2048, temperature: float = 0.1
    ) -> AsyncGenerator[str, None]:
        """Stream a completion via HuggingFace Inference API (text-generation-inference)."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                self.inference_url,
                headers={**self._headers(), "Accept": "text/event-stream"},
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": max_tokens,
                        "temperature": temperature,
                    },
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                import json as json_mod

                async for line in response.aiter_lines():
                    line = line.strip()
                    if line.startswith("data:"):
                        payload = line[5:].strip()
                        if payload:
                            data = json_mod.loads(payload)
                            token = data.get("token", {}).get("text", "")
                            if token:
                                yield token

    async def list_models(self) -> list[dict]:
        """List the configured HuggingFace model."""
        return [{"id": self.model_name, "provider": "huggingface"}]


def get_provider() -> InferenceProvider:
    """Get the configured inference provider instance.

    Returns:
        An InferenceProvider implementation based on BRIDGE_INFERENCE_PROVIDER setting.

    Raises:
        ValueError: If the configured provider is not recognized.
    """
    provider = settings.inference_provider.lower()
    if provider == "ollama":
        return OllamaProvider(settings.ollama_base_url, settings.model_name)
    elif provider == "vllm":
        return VllmProvider(settings.vllm_base_url, settings.model_name)
    elif provider == "huggingface":
        return HuggingFaceProvider(
            settings.hf_inference_url, settings.hf_api_token, settings.model_name
        )
    else:
        raise ValueError(f"Unknown inference provider: {provider}")
