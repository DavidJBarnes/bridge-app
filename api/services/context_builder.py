"""Context builder for assembling prompts with project context.

Combines project conventions, retrieved code chunks, and user prompts
into a complete context that fits within the model's token budget.
"""

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from api.models.project import Project
from api.services.retriever import retrieve_context, format_context_for_prompt
from api.services.tokenizer import count_tokens, truncate_to_tokens

logger = logging.getLogger(__name__)

# Token budget allocation
DEFAULT_CONVENTIONS_BUDGET = 300
DEFAULT_CONTEXT_BUDGET = 500
DEFAULT_OUTPUT_RESERVE = 1000
MAX_SEQUENCE_LENGTH = 2048


@dataclass
class AssembledContext:
    """Result of context assembly.

    Attributes:
        system_prompt: The system prompt including conventions.
        context: Retrieved code context to inject.
        prompt: The user's prompt.
        total_tokens: Estimated total tokens.
    """
    system_prompt: str
    context: str
    prompt: str
    total_tokens: int


def build_completion_context(
    db: Session,
    project_id: int | None,
    user_prompt: str,
    user_context: str = "",
    include_conventions: bool = True,
    max_output_tokens: int = DEFAULT_OUTPUT_RESERVE,
) -> AssembledContext:
    """Build context for a completion request.

    Assembles system prompt, conventions, retrieved context, and user
    prompt within token budget constraints.

    Args:
        db: Database session.
        project_id: Optional project ID for context injection.
        user_prompt: The user's prompt/instruction.
        user_context: Optional user-provided context (manual).
        include_conventions: Whether to include project conventions.
        max_output_tokens: Tokens to reserve for model output.

    Returns:
        AssembledContext with all prompt components.
    """
    system_prompt = ""
    context = user_context  # Start with user-provided context

    if project_id is None:
        # No project context, use defaults
        prompt_tokens = count_tokens(user_prompt)
        context_tokens = count_tokens(context)
        return AssembledContext(
            system_prompt=system_prompt,
            context=context,
            prompt=user_prompt,
            total_tokens=prompt_tokens + context_tokens,
        )

    # Load project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        logger.warning("Project %d not found, proceeding without context", project_id)
        return AssembledContext(
            system_prompt="",
            context=context,
            prompt=user_prompt,
            total_tokens=count_tokens(user_prompt) + count_tokens(context),
        )

    # Calculate token budgets
    prompt_tokens = count_tokens(user_prompt)
    user_context_tokens = count_tokens(user_context)

    available_tokens = MAX_SEQUENCE_LENGTH - max_output_tokens - prompt_tokens - user_context_tokens

    # 1. Build system prompt with conventions
    if include_conventions and project.conventions:
        conventions_budget = min(DEFAULT_CONVENTIONS_BUDGET, available_tokens // 2)
        conventions_text = truncate_to_tokens(project.conventions, conventions_budget)

        if project.system_prompt:
            system_prompt = f"{project.system_prompt}\n\n### Project Conventions\n{conventions_text}"
        else:
            system_prompt = f"### Project Conventions\n{conventions_text}"

        available_tokens -= count_tokens(system_prompt)
    elif project.system_prompt:
        system_prompt = project.system_prompt
        available_tokens -= count_tokens(system_prompt)

    # 2. Retrieve relevant context chunks
    context_budget = min(DEFAULT_CONTEXT_BUDGET, available_tokens)

    if context_budget > 50:  # Only retrieve if we have meaningful budget
        chunks = retrieve_context(
            db=db,
            project_id=project_id,
            query=user_prompt,
            top_k=5,
            max_tokens=context_budget,
        )

        if chunks:
            retrieved_context = format_context_for_prompt(chunks)

            # Combine with user context
            if user_context:
                context = f"{user_context}\n\n{retrieved_context}"
            else:
                context = retrieved_context

            logger.debug(
                "Injected %d chunks (%d tokens) for project %d",
                len(chunks),
                sum(c.token_count for c in chunks),
                project_id,
            )

    total_tokens = (
        count_tokens(system_prompt) +
        count_tokens(context) +
        prompt_tokens
    )

    return AssembledContext(
        system_prompt=system_prompt,
        context=context,
        prompt=user_prompt,
        total_tokens=total_tokens,
    )


def build_chat_context(
    db: Session,
    project_id: int | None,
    messages: list[dict],
    include_conventions: bool = True,
    max_output_tokens: int = DEFAULT_OUTPUT_RESERVE,
) -> tuple[str, list[dict]]:
    """Build context for a chat request.

    Modifies the message list to include project context in the system
    message and retrieves relevant chunks based on the conversation.

    Args:
        db: Database session.
        project_id: Optional project ID for context injection.
        messages: List of chat messages.
        include_conventions: Whether to include project conventions.
        max_output_tokens: Tokens to reserve for model output.

    Returns:
        Tuple of (system_prompt, modified_messages).
    """
    if project_id is None:
        return "", messages

    # Load project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        logger.warning("Project %d not found for chat", project_id)
        return "", messages

    # Build system prompt
    system_prompt = ""
    if include_conventions and project.conventions:
        conventions_text = truncate_to_tokens(project.conventions, DEFAULT_CONVENTIONS_BUDGET)
        if project.system_prompt:
            system_prompt = f"{project.system_prompt}\n\n### Project Conventions\n{conventions_text}"
        else:
            system_prompt = f"### Project Conventions\n{conventions_text}"
    elif project.system_prompt:
        system_prompt = project.system_prompt

    # Extract user query from last user message for retrieval
    last_user_msg = None
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    if not last_user_msg:
        return system_prompt, messages

    # Calculate available budget
    messages_tokens = sum(count_tokens(m.get("content", "")) for m in messages)
    system_tokens = count_tokens(system_prompt)
    available = MAX_SEQUENCE_LENGTH - max_output_tokens - messages_tokens - system_tokens

    context_budget = min(DEFAULT_CONTEXT_BUDGET, available)

    if context_budget > 50:
        chunks = retrieve_context(
            db=db,
            project_id=project_id,
            query=last_user_msg,
            top_k=3,
            max_tokens=context_budget,
        )

        if chunks:
            retrieved_context = format_context_for_prompt(chunks)
            # Add context as a system message
            system_prompt = f"{system_prompt}\n\n{retrieved_context}" if system_prompt else retrieved_context

    return system_prompt, messages
