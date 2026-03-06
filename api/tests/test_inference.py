"""Tests for inference service prompt formatting and provider selection."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from api.services.inference import (
    format_alpaca_prompt,
    format_chat_messages,
    get_provider,
    OllamaProvider,
    VllmProvider,
    HuggingFaceProvider,
)


def test_format_alpaca_prompt_basic():
    """Basic prompt is wrapped in Alpaca instruction format."""
    result = format_alpaca_prompt("Write a hello world")
    assert "### Instruction:" in result
    assert "Write a hello world" in result
    assert "### Response:" in result


def test_format_alpaca_prompt_with_context():
    """Prompt with context includes Input section."""
    result = format_alpaca_prompt("Explain this", "some code here")
    assert "### Input:" in result
    assert "some code here" in result
    assert "paired with further context" in result


def test_format_chat_messages_single():
    """Single user message is formatted correctly."""
    messages = [{"role": "user", "content": "Hello"}]
    result = format_chat_messages(messages)
    assert "User: Hello" in result
    assert "### Instruction:" in result


def test_format_chat_messages_multi_turn():
    """Multi-turn conversation combines all messages."""
    messages = [
        {"role": "system", "content": "You are a coding assistant"},
        {"role": "user", "content": "Write a function"},
        {"role": "assistant", "content": "Here is a function"},
        {"role": "user", "content": "Add error handling"},
    ]
    result = format_chat_messages(messages)
    assert "System: You are a coding assistant" in result
    assert "User: Write a function" in result
    assert "Assistant: Here is a function" in result
    assert "User: Add error handling" in result


def test_format_chat_messages_missing_fields():
    """Messages with missing fields use defaults."""
    messages = [{"content": "test"}, {"role": "user"}]
    result = format_chat_messages(messages)
    assert "User: test" in result


def test_get_provider_ollama():
    """Ollama provider is returned when configured."""
    with patch("api.services.inference.settings") as mock_settings:
        mock_settings.inference_provider = "ollama"
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.model_name = "test-model"
        provider = get_provider()
        assert isinstance(provider, OllamaProvider)


def test_get_provider_vllm():
    """vLLM provider is returned when configured."""
    with patch("api.services.inference.settings") as mock_settings:
        mock_settings.inference_provider = "vllm"
        mock_settings.vllm_base_url = "http://localhost:8001"
        mock_settings.model_name = "test-model"
        provider = get_provider()
        assert isinstance(provider, VllmProvider)


def test_get_provider_huggingface():
    """HuggingFace provider is returned when configured."""
    with patch("api.services.inference.settings") as mock_settings:
        mock_settings.inference_provider = "huggingface"
        mock_settings.hf_inference_url = "https://example.com"
        mock_settings.hf_api_token = "test-token"
        mock_settings.model_name = "test-model"
        provider = get_provider()
        assert isinstance(provider, HuggingFaceProvider)


def test_get_provider_unknown():
    """Unknown provider raises ValueError."""
    with patch("api.services.inference.settings") as mock_settings:
        mock_settings.inference_provider = "unknown"
        with pytest.raises(ValueError, match="Unknown inference provider"):
            get_provider()


@pytest.mark.asyncio
async def test_ollama_generate():
    """OllamaProvider.generate calls the correct endpoint."""
    provider = OllamaProvider("http://localhost:11434", "test-model")
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "generated code"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await provider.generate("test prompt")
        assert result == "generated code"


@pytest.mark.asyncio
async def test_ollama_list_models():
    """OllamaProvider.list_models returns formatted model list."""
    provider = OllamaProvider("http://localhost:11434", "test-model")
    mock_response = MagicMock()
    mock_response.json.return_value = {"models": [{"name": "model1"}, {"name": "model2"}]}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        models = await provider.list_models()
        assert len(models) == 2
        assert models[0]["id"] == "model1"
        assert models[0]["provider"] == "ollama"


@pytest.mark.asyncio
async def test_vllm_generate():
    """VllmProvider.generate calls the OpenAI-compatible endpoint."""
    provider = VllmProvider("http://localhost:8001", "test-model")
    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": [{"text": "vllm output"}]}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await provider.generate("test prompt")
        assert result == "vllm output"


@pytest.mark.asyncio
async def test_vllm_list_models():
    """VllmProvider.list_models returns formatted model list."""
    provider = VllmProvider("http://localhost:8001", "test-model")
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [{"id": "vllm-model"}]}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        models = await provider.list_models()
        assert len(models) == 1
        assert models[0]["id"] == "vllm-model"
        assert models[0]["provider"] == "vllm"


@pytest.mark.asyncio
async def test_huggingface_generate():
    """HuggingFaceProvider.generate calls the inference endpoint."""
    provider = HuggingFaceProvider("https://example.com", "token", "test-model")
    mock_response = MagicMock()
    mock_response.json.return_value = [{"generated_text": "hf output"}]
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await provider.generate("test prompt")
        assert result == "hf output"


@pytest.mark.asyncio
async def test_huggingface_generate_dict_response():
    """HuggingFaceProvider handles dict response format."""
    provider = HuggingFaceProvider("https://example.com", "token", "test-model")
    mock_response = MagicMock()
    mock_response.json.return_value = {"generated_text": "hf dict output"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await provider.generate("test prompt")
        assert result == "hf dict output"


@pytest.mark.asyncio
async def test_huggingface_list_models():
    """HuggingFaceProvider.list_models returns configured model."""
    provider = HuggingFaceProvider("https://example.com", "token", "my-model")
    models = await provider.list_models()
    assert len(models) == 1
    assert models[0]["id"] == "my-model"
    assert models[0]["provider"] == "huggingface"


def test_huggingface_headers():
    """HuggingFaceProvider builds correct auth headers."""
    provider = HuggingFaceProvider("https://example.com", "my-token", "model")
    headers = provider._headers()
    assert headers["Authorization"] == "Bearer my-token"


class MockAsyncLines:
    """Mock async iterator for response.aiter_lines()."""

    def __init__(self, lines):
        self.lines = iter(lines)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.lines)
        except StopIteration:
            raise StopAsyncIteration


@pytest.mark.asyncio
async def test_ollama_generate_stream():
    """OllamaProvider.generate_stream yields tokens."""
    import json as json_mod

    provider = OllamaProvider("http://localhost:11434", "test-model")
    lines = [
        json_mod.dumps({"response": "Hello"}),
        json_mod.dumps({"response": " World"}),
        json_mod.dumps({"done": True}),
    ]

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.aiter_lines = lambda: MockAsyncLines(lines)
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        tokens = []
        async for token in provider.generate_stream("test"):
            tokens.append(token)
        assert tokens == ["Hello", " World"]


@pytest.mark.asyncio
async def test_vllm_generate_stream():
    """VllmProvider.generate_stream yields tokens from SSE."""
    provider = VllmProvider("http://localhost:8001", "test-model")
    lines = [
        'data: {"choices":[{"text":"Hello"}]}',
        'data: {"choices":[{"text":" World"}]}',
        "data: [DONE]",
    ]

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.aiter_lines = lambda: MockAsyncLines(lines)
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        tokens = []
        async for token in provider.generate_stream("test"):
            tokens.append(token)
        assert tokens == ["Hello", " World"]


@pytest.mark.asyncio
async def test_huggingface_generate_stream():
    """HuggingFaceProvider.generate_stream yields tokens from SSE."""
    provider = HuggingFaceProvider("https://example.com", "token", "test-model")
    lines = [
        'data:{"token":{"text":"Hello"}}',
        'data:{"token":{"text":" World"}}',
    ]

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.aiter_lines = lambda: MockAsyncLines(lines)
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        tokens = []
        async for token in provider.generate_stream("test"):
            tokens.append(token)
        assert tokens == ["Hello", " World"]
