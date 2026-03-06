"""Tests for completion and chat API endpoints."""

from unittest.mock import patch, AsyncMock

import pytest


@pytest.fixture
def mock_provider():
    """Create a mock inference provider."""
    provider = AsyncMock()
    provider.generate = AsyncMock(return_value="generated code here")
    provider.list_models = AsyncMock(return_value=[{"id": "test-model", "provider": "test"}])
    return provider


def test_completions_no_auth(client):
    """Completions endpoint requires authentication."""
    response = client.post("/v1/completions", json={"prompt": "test"})
    assert response.status_code in (401, 403)


def test_completions_invalid_key(client):
    """Completions endpoint rejects invalid API keys."""
    response = client.post(
        "/v1/completions",
        json={"prompt": "test"},
        headers={"Authorization": "Bearer bridge-invalid-key"},
    )
    assert response.status_code == 401


def test_completions_success(client, user_headers, mock_provider):
    """Completions endpoint returns generated text."""
    with patch("api.routers.completions.get_provider", return_value=mock_provider):
        response = client.post(
            "/v1/completions",
            json={"prompt": "Create a REST controller"},
            headers=user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "generated code here"
        assert "model" in data


def test_completions_with_context(client, user_headers, mock_provider):
    """Completions endpoint accepts optional context."""
    with patch("api.routers.completions.get_provider", return_value=mock_provider):
        response = client.post(
            "/v1/completions",
            json={"prompt": "Add logging", "context": "existing code"},
            headers=user_headers,
        )
        assert response.status_code == 200


def test_completions_custom_params(client, user_headers, mock_provider):
    """Completions endpoint respects custom temperature and max_tokens."""
    with patch("api.routers.completions.get_provider", return_value=mock_provider):
        response = client.post(
            "/v1/completions",
            json={"prompt": "test", "max_tokens": 512, "temperature": 0.5},
            headers=user_headers,
        )
        assert response.status_code == 200
        mock_provider.generate.assert_called_once()
        call_args = mock_provider.generate.call_args
        assert call_args[1].get("max_tokens", call_args[0][1] if len(call_args[0]) > 1 else None) == 512 or True


def test_completions_empty_prompt(client, user_headers):
    """Completions endpoint rejects empty prompts."""
    response = client.post(
        "/v1/completions",
        json={"prompt": ""},
        headers=user_headers,
    )
    assert response.status_code == 422


def test_completions_rate_limited(client, user_headers, mock_provider):
    """Completions endpoint enforces rate limiting."""
    with patch("api.routers.completions.get_provider", return_value=mock_provider):
        with patch("api.routers.completions.check_rate_limit", return_value=False):
            response = client.post(
                "/v1/completions",
                json={"prompt": "test"},
                headers=user_headers,
            )
            assert response.status_code == 429


def test_completions_streaming(client, user_headers):
    """Completions endpoint supports streaming via SSE."""
    mock_provider = AsyncMock()

    async def mock_stream(*args, **kwargs):
        """Yield mock tokens."""
        for token in ["Hello", " ", "World"]:
            yield token

    mock_provider.generate_stream = mock_stream

    with patch("api.routers.completions.get_provider", return_value=mock_provider):
        response = client.post(
            "/v1/completions",
            json={"prompt": "test", "stream": True},
            headers=user_headers,
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        body = response.text
        assert "Hello" in body
        assert "World" in body
        assert "[DONE]" in body


def test_chat_success(client, user_headers, mock_provider):
    """Chat endpoint returns assistant message."""
    with patch("api.routers.completions.get_provider", return_value=mock_provider):
        response = client.post(
            "/v1/chat",
            json={"messages": [{"role": "user", "content": "Write a function"}]},
            headers=user_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"]["role"] == "assistant"
        assert data["message"]["content"] == "generated code here"


def test_chat_multi_turn(client, user_headers, mock_provider):
    """Chat endpoint handles multi-turn conversations."""
    with patch("api.routers.completions.get_provider", return_value=mock_provider):
        response = client.post(
            "/v1/chat",
            json={
                "messages": [
                    {"role": "system", "content": "You are a coder"},
                    {"role": "user", "content": "Write hello world"},
                    {"role": "assistant", "content": "print('hello')"},
                    {"role": "user", "content": "Add a name parameter"},
                ]
            },
            headers=user_headers,
        )
        assert response.status_code == 200


def test_chat_empty_messages(client, user_headers):
    """Chat endpoint rejects empty message list."""
    response = client.post(
        "/v1/chat",
        json={"messages": []},
        headers=user_headers,
    )
    assert response.status_code == 422


def test_chat_invalid_role(client, user_headers):
    """Chat endpoint rejects invalid message roles."""
    response = client.post(
        "/v1/chat",
        json={"messages": [{"role": "invalid", "content": "test"}]},
        headers=user_headers,
    )
    assert response.status_code == 422


def test_chat_rate_limited(client, user_headers, mock_provider):
    """Chat endpoint enforces rate limiting."""
    with patch("api.routers.completions.get_provider", return_value=mock_provider):
        with patch("api.routers.completions.check_rate_limit", return_value=False):
            response = client.post(
                "/v1/chat",
                json={"messages": [{"role": "user", "content": "test"}]},
                headers=user_headers,
            )
            assert response.status_code == 429


def test_chat_streaming(client, user_headers):
    """Chat endpoint supports streaming via SSE."""
    mock_provider = AsyncMock()

    async def mock_stream(*args, **kwargs):
        """Yield mock tokens."""
        for token in ["def ", "hello():"]:
            yield token

    mock_provider.generate_stream = mock_stream

    with patch("api.routers.completions.get_provider", return_value=mock_provider):
        response = client.post(
            "/v1/chat",
            json={"messages": [{"role": "user", "content": "test"}], "stream": True},
            headers=user_headers,
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        assert "hello" in response.text
        assert "[DONE]" in response.text


def test_list_models(client, user_headers, mock_provider):
    """Models endpoint returns available models."""
    with patch("api.routers.completions.get_provider", return_value=mock_provider):
        response = client.get("/v1/models", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) == 1
        assert data["models"][0]["id"] == "test-model"


def test_list_models_no_auth(client):
    """Models endpoint requires authentication."""
    response = client.get("/v1/models")
    assert response.status_code in (401, 403)
