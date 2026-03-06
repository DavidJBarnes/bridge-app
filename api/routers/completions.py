"""Completion and chat endpoints for code generation."""

import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.config import settings
from api.database import get_db
from api.dependencies import get_current_api_key
from api.models.api_key import ApiKey
from api.models.usage_log import UsageLog
from api.services.auth import check_rate_limit
from api.services.inference import (
    format_alpaca_prompt,
    format_chat_messages,
    get_provider,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["inference"])


class CompletionRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    context: str = ""
    max_tokens: int = Field(default=2048, ge=1, le=8192)
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    stream: bool = False


class CompletionResponse(BaseModel):
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1)
    max_tokens: int = Field(default=2048, ge=1, le=8192)
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    stream: bool = False


class ChatResponse(BaseModel):
    message: ChatMessage
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


@router.post("/completions", response_model=CompletionResponse)
async def create_completion(
    request: CompletionRequest,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Generate a code completion from a prompt.

    Formats the prompt in Alpaca instruction format and sends it to the
    configured inference provider.
    """
    if not check_rate_limit(db, api_key.id, settings.rate_limit_per_minute):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    provider = get_provider()
    formatted_prompt = format_alpaca_prompt(request.prompt, request.context)
    start = time.time()

    if request.stream:
        return _stream_completion(provider, formatted_prompt, request, db, api_key, start)

    text = await provider.generate(formatted_prompt, request.max_tokens, request.temperature)
    duration = time.time() - start

    _log_usage(db, api_key.id, "/v1/completions", 0, len(text.split()), duration)
    logger.info("Completion generated in %.2fs for key '%s'", duration, api_key.name)

    return CompletionResponse(text=text, model=settings.model_name)


def _stream_completion(provider, formatted_prompt, request, db, api_key, start):
    """Create a streaming response for completion requests.

    Args:
        provider: The inference provider.
        formatted_prompt: The formatted prompt string.
        request: The original completion request.
        db: Database session.
        api_key: The authenticated API key.
        start: Request start timestamp.

    Returns:
        A StreamingResponse with SSE-formatted tokens.
    """

    async def event_stream():
        """Yield SSE events for each generated token."""
        token_count = 0
        async for token in provider.generate_stream(
            formatted_prompt, request.max_tokens, request.temperature
        ):
            token_count += 1
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"
        duration = time.time() - start
        _log_usage(db, api_key.id, "/v1/completions", 0, token_count, duration)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/chat", response_model=ChatResponse)
async def create_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Generate a chat response from a conversation history.

    Converts the message history into an Alpaca-formatted prompt and
    generates a response.
    """
    if not check_rate_limit(db, api_key.id, settings.rate_limit_per_minute):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    provider = get_provider()
    messages_dicts = [{"role": m.role, "content": m.content} for m in request.messages]
    formatted_prompt = format_chat_messages(messages_dicts)
    start = time.time()

    if request.stream:
        return _stream_chat(provider, formatted_prompt, request, db, api_key, start)

    text = await provider.generate(formatted_prompt, request.max_tokens, request.temperature)
    duration = time.time() - start

    _log_usage(db, api_key.id, "/v1/chat", 0, len(text.split()), duration)
    logger.info("Chat response generated in %.2fs for key '%s'", duration, api_key.name)

    return ChatResponse(
        message=ChatMessage(role="assistant", content=text),
        model=settings.model_name,
    )


def _stream_chat(provider, formatted_prompt, request, db, api_key, start):
    """Create a streaming response for chat requests.

    Args:
        provider: The inference provider.
        formatted_prompt: The formatted prompt string.
        request: The original chat request.
        db: Database session.
        api_key: The authenticated API key.
        start: Request start timestamp.

    Returns:
        A StreamingResponse with SSE-formatted tokens.
    """

    async def event_stream():
        """Yield SSE events for each generated token."""
        token_count = 0
        async for token in provider.generate_stream(
            formatted_prompt, request.max_tokens, request.temperature
        ):
            token_count += 1
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"
        duration = time.time() - start
        _log_usage(db, api_key.id, "/v1/chat", 0, token_count, duration)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/models")
async def list_models(api_key: ApiKey = Depends(get_current_api_key)):
    """List available models from the configured inference provider."""
    provider = get_provider()
    models = await provider.list_models()
    return {"models": models}


def _log_usage(
    db: Session,
    api_key_id: int,
    endpoint: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration: float,
    status_code: int = 200,
    error_message: str | None = None,
):
    """Record an API usage log entry.

    Args:
        db: Database session.
        api_key_id: ID of the API key used.
        endpoint: The API endpoint called.
        prompt_tokens: Number of prompt tokens.
        completion_tokens: Number of completion tokens.
        duration: Request duration in seconds.
        status_code: HTTP status code of the response.
        error_message: Optional error message if the request failed.
    """
    log = UsageLog(
        api_key_id=api_key_id,
        endpoint=endpoint,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        duration_seconds=duration,
        status_code=status_code,
        error_message=error_message,
    )
    db.add(log)
    db.commit()
