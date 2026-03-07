"""Token counting utilities for context budget management.

Uses tiktoken for fast, accurate token counting compatible with
most LLM tokenizers including DeepSeek-Coder.
"""

import logging
from functools import lru_cache

import tiktoken

logger = logging.getLogger(__name__)

# Use cl100k_base encoding (GPT-4/Claude compatible, close enough for DeepSeek)
_ENCODING_NAME = "cl100k_base"


@lru_cache(maxsize=1)
def _get_encoding():
    """Get the tiktoken encoding, cached for performance.

    Returns:
        The tiktoken Encoding instance.
    """
    return tiktoken.get_encoding(_ENCODING_NAME)


def count_tokens(text: str) -> int:
    """Count the number of tokens in a text string.

    Args:
        text: The text to tokenize.

    Returns:
        The number of tokens.
    """
    if not text:
        return 0
    encoding = _get_encoding()
    return len(encoding.encode(text))


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to fit within a token budget.

    Args:
        text: The text to truncate.
        max_tokens: Maximum number of tokens allowed.

    Returns:
        The truncated text.
    """
    if not text or max_tokens <= 0:
        return ""

    encoding = _get_encoding()
    tokens = encoding.encode(text)

    if len(tokens) <= max_tokens:
        return text

    truncated_tokens = tokens[:max_tokens]
    return encoding.decode(truncated_tokens)


def estimate_tokens(text: str) -> int:
    """Fast token estimate without full tokenization.

    Uses a simple heuristic: ~4 characters per token for code.
    Use count_tokens() when accuracy matters.

    Args:
        text: The text to estimate.

    Returns:
        Estimated token count.
    """
    if not text:
        return 0
    # Code averages ~4 chars per token (more dense than prose)
    return len(text) // 4
