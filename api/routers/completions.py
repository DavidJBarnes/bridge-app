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
from api.services.context_builder import build_completion_context, build_chat_context
from api.services.inference import (
    format_alpaca_prompt,
    format_chat_messages,
    get_provider,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["inference"])


class CompletionRequest(BaseModel):
    """Request for code completion.

    Attributes:
        prompt: The instruction or question.
        context: Optional manual context to include.
        project_id: Optional project ID for automatic context injection.
        include_conventions: Whether to include project conventions.
        max_tokens: Maximum tokens to generate.
        temperature: Sampling temperature.
        stream: Whether to stream the response.
    """
    prompt: str = Field(..., min_length=1)
    context: str = ""
    project_id: int | None = None
    include_conventions: bool = True
    max_tokens: int = Field(default=2048, ge=1, le=8192)
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    stream: bool = False


class CompletionResponse(BaseModel):
    """Response from code completion."""
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    project_id: int | None = None
    context_chunks: int = 0


class ChatMessage(BaseModel):
    """A chat message."""
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    """Request for chat completion.

    Attributes:
        messages: Conversation history.
        project_id: Optional project ID for automatic context injection.
        include_conventions: Whether to include project conventions.
        max_tokens: Maximum tokens to generate.
        temperature: Sampling temperature.
        stream: Whether to stream the response.
    """
    messages: list[ChatMessage] = Field(..., min_length=1)
    project_id: int | None = None
    include_conventions: bool = True
    max_tokens: int = Field(default=2048, ge=1, le=8192)
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    stream: bool = False


class ChatResponse(BaseModel):
    """Response from chat completion."""
    message: ChatMessage
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    project_id: int | None = None
    context_chunks: int = 0


@router.post("/completions", response_model=CompletionResponse)
async def create_completion(
    request: CompletionRequest,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Generate a code completion from a prompt.

    If project_id is provided, automatically retrieves relevant code
    context from the project and injects it into the prompt.
    """
    if not check_rate_limit(db, api_key.id, settings.rate_limit_per_minute):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Build context with project injection
    assembled = build_completion_context(
        db=db,
        project_id=request.project_id,
        user_prompt=request.prompt,
        user_context=request.context,
        include_conventions=request.include_conventions,
        max_output_tokens=request.max_tokens,
    )

    # Format the full prompt
    if assembled.system_prompt:
        full_context = f"{assembled.system_prompt}\n\n{assembled.context}" if assembled.context else assembled.system_prompt
    else:
        full_context = assembled.context

    provider = get_provider()
    formatted_prompt = format_alpaca_prompt(assembled.prompt, full_context)
    start = time.time()

    if request.stream:
        return _stream_completion(
            provider, formatted_prompt, request, db, api_key, start
        )

    text = await provider.generate(
        formatted_prompt, request.max_tokens, request.temperature
    )
    duration = time.time() - start

    _log_usage(
        db, api_key.id, "/v1/completions",
        assembled.total_tokens, len(text.split()), duration,
        project_id=request.project_id,
    )
    logger.info(
        "Completion generated in %.2fs for key '%s' (project=%s, context_tokens=%d)",
        duration, api_key.name, request.project_id, assembled.total_tokens,
    )

    return CompletionResponse(
        text=text,
        model=settings.model_name,
        prompt_tokens=assembled.total_tokens,
        project_id=request.project_id,
    )


def _stream_completion(provider, formatted_prompt, request, db, api_key, start):
    """Create a streaming response for completion requests."""

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
        _log_usage(
            db, api_key.id, "/v1/completions", 0, token_count, duration,
            project_id=request.project_id,
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/chat", response_model=ChatResponse)
async def create_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Generate a chat response from a conversation history.

    If project_id is provided, automatically retrieves relevant code
    context and includes it with the system prompt.
    """
    if not check_rate_limit(db, api_key.id, settings.rate_limit_per_minute):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    messages_dicts = [{"role": m.role, "content": m.content} for m in request.messages]

    # Build context with project injection
    system_prompt, modified_messages = build_chat_context(
        db=db,
        project_id=request.project_id,
        messages=messages_dicts,
        include_conventions=request.include_conventions,
        max_output_tokens=request.max_tokens,
    )

    # Prepend system message if we have context
    if system_prompt:
        modified_messages = [
            {"role": "system", "content": system_prompt}
        ] + modified_messages

    provider = get_provider()
    formatted_prompt = format_chat_messages(modified_messages)
    start = time.time()

    if request.stream:
        return _stream_chat(
            provider, formatted_prompt, request, db, api_key, start
        )

    text = await provider.generate(
        formatted_prompt, request.max_tokens, request.temperature
    )
    duration = time.time() - start

    _log_usage(
        db, api_key.id, "/v1/chat", 0, len(text.split()), duration,
        project_id=request.project_id,
    )
    logger.info(
        "Chat response generated in %.2fs for key '%s' (project=%s)",
        duration, api_key.name, request.project_id,
    )

    return ChatResponse(
        message=ChatMessage(role="assistant", content=text),
        model=settings.model_name,
        project_id=request.project_id,
    )


def _stream_chat(provider, formatted_prompt, request, db, api_key, start):
    """Create a streaming response for chat requests."""

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
        _log_usage(
            db, api_key.id, "/v1/chat", 0, token_count, duration,
            project_id=request.project_id,
        )

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
    project_id: int | None = None,
):
    """Record an API usage log entry."""
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
