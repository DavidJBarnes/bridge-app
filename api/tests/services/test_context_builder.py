"""Tests for the context builder service."""

import pytest
from unittest.mock import MagicMock, patch

from api.services.context_builder import (
    build_completion_context,
    build_chat_context,
    AssembledContext,
)


class TestBuildCompletionContext:
    """Tests for build_completion_context."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()

    def test_no_project_returns_user_prompt(self, mock_db):
        """Without project, returns just user prompt."""
        result = build_completion_context(
            db=mock_db,
            project_id=None,
            user_prompt="Create a REST controller",
            user_context="",
        )

        assert result.prompt == "Create a REST controller"
        assert result.system_prompt == ""
        assert result.context == ""

    def test_with_user_context(self, mock_db):
        """User context is preserved."""
        result = build_completion_context(
            db=mock_db,
            project_id=None,
            user_prompt="Fix the bug",
            user_context="Current code: def foo(): pass",
        )

        assert result.context == "Current code: def foo(): pass"

    def test_missing_project_returns_prompt_only(self, mock_db):
        """Missing project ID proceeds without context."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = build_completion_context(
            db=mock_db,
            project_id=999,
            user_prompt="Test prompt",
        )

        assert result.system_prompt == ""
        assert result.prompt == "Test prompt"

    def test_project_conventions_included(self, mock_db):
        """Project conventions are included in system prompt."""
        mock_project = MagicMock()
        mock_project.conventions = "# Conventions\n- Use 4 spaces"
        mock_project.system_prompt = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_project

        with patch("api.services.context_builder.retrieve_context", return_value=[]):
            result = build_completion_context(
                db=mock_db,
                project_id=1,
                user_prompt="Create a service",
                include_conventions=True,
            )

        assert "Conventions" in result.system_prompt
        assert "4 spaces" in result.system_prompt

    def test_project_system_prompt_included(self, mock_db):
        """Project system prompt is included."""
        mock_project = MagicMock()
        mock_project.conventions = None
        mock_project.system_prompt = "You are a Spring Boot expert."
        mock_db.query.return_value.filter.return_value.first.return_value = mock_project

        with patch("api.services.context_builder.retrieve_context", return_value=[]):
            result = build_completion_context(
                db=mock_db,
                project_id=1,
                user_prompt="Create a service",
            )

        assert "Spring Boot expert" in result.system_prompt

    def test_retrieved_context_included(self, mock_db):
        """Retrieved chunks are included in context."""
        mock_project = MagicMock()
        mock_project.conventions = None
        mock_project.system_prompt = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_project

        mock_chunk = MagicMock()
        mock_chunk.content = "public User createUser() { }"
        mock_chunk.chunk = MagicMock()
        mock_chunk.chunk.signature = "createUser()"
        mock_chunk.file_path = "UserService.java"
        mock_chunk.token_count = 20

        with patch("api.services.context_builder.retrieve_context", return_value=[mock_chunk]):
            result = build_completion_context(
                db=mock_db,
                project_id=1,
                user_prompt="Create a user",
            )

        assert "UserService.java" in result.context or "createUser" in result.context

    def test_conventions_excluded_when_disabled(self, mock_db):
        """Conventions excluded when include_conventions=False."""
        mock_project = MagicMock()
        mock_project.conventions = "# Should not appear"
        mock_project.system_prompt = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_project

        with patch("api.services.context_builder.retrieve_context", return_value=[]):
            result = build_completion_context(
                db=mock_db,
                project_id=1,
                user_prompt="Test",
                include_conventions=False,
            )

        assert "Should not appear" not in result.system_prompt


class TestBuildChatContext:
    """Tests for build_chat_context."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()

    def test_no_project_returns_original_messages(self, mock_db):
        """Without project, returns original messages."""
        messages = [{"role": "user", "content": "Hello"}]

        system_prompt, result_messages = build_chat_context(
            db=mock_db,
            project_id=None,
            messages=messages,
        )

        assert system_prompt == ""
        assert result_messages == messages

    def test_project_context_added_to_system(self, mock_db):
        """Project context is added to system prompt."""
        mock_project = MagicMock()
        mock_project.conventions = "Use TypeScript"
        mock_project.system_prompt = "You are helpful."
        mock_db.query.return_value.filter.return_value.first.return_value = mock_project

        messages = [{"role": "user", "content": "Help me code"}]

        with patch("api.services.context_builder.retrieve_context", return_value=[]):
            system_prompt, result_messages = build_chat_context(
                db=mock_db,
                project_id=1,
                messages=messages,
            )

        assert "You are helpful" in system_prompt
        assert "TypeScript" in system_prompt

    def test_extracts_last_user_message_for_retrieval(self, mock_db):
        """Uses last user message for context retrieval."""
        mock_project = MagicMock()
        mock_project.conventions = None
        mock_project.system_prompt = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_project

        messages = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Create a UserService"},
        ]

        with patch("api.services.context_builder.retrieve_context") as mock_retrieve:
            mock_retrieve.return_value = []
            build_chat_context(
                db=mock_db,
                project_id=1,
                messages=messages,
            )

            # Verify retrieve was called with last user message
            mock_retrieve.assert_called_once()
            call_args = mock_retrieve.call_args
            assert "UserService" in call_args.kwargs.get("query", "")
