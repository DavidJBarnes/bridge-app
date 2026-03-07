"""Tests for the tokenizer utilities."""

import pytest

from api.services.tokenizer import count_tokens, truncate_to_tokens, estimate_tokens


class TestCountTokens:
    """Tests for token counting."""

    def test_empty_string(self):
        """Empty string returns 0 tokens."""
        assert count_tokens("") == 0

    def test_none_returns_zero(self):
        """None returns 0 tokens."""
        assert count_tokens(None) == 0  # type: ignore

    def test_simple_text(self):
        """Counts tokens in simple text."""
        # "Hello, world!" is typically 4 tokens
        count = count_tokens("Hello, world!")
        assert 2 <= count <= 6

    def test_code_snippet(self):
        """Counts tokens in code."""
        code = "def hello():\n    print('Hello')"
        count = count_tokens(code)
        assert count > 5

    def test_long_text(self):
        """Handles long text correctly."""
        long_text = "word " * 1000
        count = count_tokens(long_text)
        # Should be roughly 1000 tokens (1 per word)
        assert 900 <= count <= 1100


class TestTruncateToTokens:
    """Tests for token truncation."""

    def test_short_text_unchanged(self):
        """Short text is returned unchanged."""
        text = "Hello, world!"
        result = truncate_to_tokens(text, max_tokens=100)
        assert result == text

    def test_long_text_truncated(self):
        """Long text is truncated to max tokens."""
        long_text = "word " * 100
        result = truncate_to_tokens(long_text, max_tokens=10)

        # Result should have fewer tokens
        result_tokens = count_tokens(result)
        assert result_tokens <= 10

    def test_empty_string(self):
        """Empty string returns empty string."""
        assert truncate_to_tokens("", 100) == ""

    def test_zero_max_tokens(self):
        """Zero max tokens returns empty string."""
        assert truncate_to_tokens("Hello", 0) == ""


class TestEstimateTokens:
    """Tests for fast token estimation."""

    def test_empty_string(self):
        """Empty string estimates to 0."""
        assert estimate_tokens("") == 0

    def test_rough_estimate(self):
        """Estimate is roughly correct for code."""
        code = "public class User { }"  # ~20 chars = ~5 token estimate
        estimate = estimate_tokens(code)
        actual = count_tokens(code)

        # Should be within 2x of actual
        assert estimate > 0
        assert actual / 3 <= estimate <= actual * 3
