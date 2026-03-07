"""Tests for the TF-IDF retrieval service."""

import pytest
from unittest.mock import MagicMock, patch

from api.services.retriever import (
    CodeTokenizer,
    ProjectRetriever,
    RetrievedChunk,
    retrieve_context,
    format_context_for_prompt,
    clear_retriever_cache,
)
from api.models.file_chunk import FileChunk
from api.models.project_file import ProjectFile


class TestCodeTokenizer:
    """Tests for the custom code tokenizer."""

    def test_camel_case_split(self):
        """Splits camelCase identifiers."""
        tokenizer = CodeTokenizer()
        tokens = tokenizer("getUserById")

        assert "get" in tokens
        assert "user" in tokens
        assert "by" in tokens
        assert "id" in tokens

    def test_snake_case_split(self):
        """Splits snake_case identifiers."""
        tokenizer = CodeTokenizer()
        tokens = tokenizer("get_user_by_id")

        assert "get" in tokens
        assert "user" in tokens
        assert "by" in tokens
        assert "id" in tokens

    def test_mixed_case(self):
        """Handles mixed case styles."""
        tokenizer = CodeTokenizer()
        tokens = tokenizer("createUser_withRole")

        assert "create" in tokens
        assert "user" in tokens
        assert "with" in tokens
        assert "role" in tokens

    def test_preserves_keywords(self):
        """Preserves programming keywords."""
        tokenizer = CodeTokenizer()
        tokens = tokenizer("public class User extends BaseEntity")

        assert "public" in tokens
        assert "class" in tokens
        assert "user" in tokens
        assert "extends" in tokens

    def test_filters_short_tokens(self):
        """Filters out single-character tokens."""
        tokenizer = CodeTokenizer()
        tokens = tokenizer("int x = y + z")

        # Single chars should be filtered
        assert "x" not in tokens
        assert "y" not in tokens
        assert "z" not in tokens
        # But "int" should remain
        assert "int" in tokens

    def test_handles_numbers(self):
        """Handles alphanumeric identifiers."""
        tokenizer = CodeTokenizer()
        tokens = tokenizer("user123 page2Controller")

        assert "user123" in tokens or "user" in tokens
        assert "page2" in tokens or "page" in tokens
        assert "controller" in tokens


class TestProjectRetriever:
    """Tests for the ProjectRetriever class."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def sample_chunks(self):
        """Create sample chunks for testing."""
        chunks = [
            (
                MagicMock(
                    id=1,
                    content="public User createUser(CreateUserRequest request) { return userRepository.save(new User(request)); }",
                    signature="public User createUser(CreateUserRequest request)",
                    chunk_type="method",
                    token_count=25,
                ),
                "UserService.java"
            ),
            (
                MagicMock(
                    id=2,
                    content="public void deleteUser(Long id) { userRepository.deleteById(id); }",
                    signature="public void deleteUser(Long id)",
                    chunk_type="method",
                    token_count=15,
                ),
                "UserService.java"
            ),
            (
                MagicMock(
                    id=3,
                    content="public String authenticate(LoginRequest request) { return jwtService.generateToken(user); }",
                    signature="public String authenticate(LoginRequest request)",
                    chunk_type="method",
                    token_count=20,
                ),
                "AuthService.java"
            ),
            (
                MagicMock(
                    id=4,
                    content="export const useAuth = () => { const [user, setUser] = useState(null); return { user, login, logout }; }",
                    signature="export const useAuth",
                    chunk_type="function",
                    token_count=30,
                ),
                "useAuth.ts"
            ),
        ]
        return chunks

    def test_build_index(self, mock_db_session, sample_chunks):
        """Builds TF-IDF index from database chunks."""
        # Setup mock query
        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = sample_chunks
        mock_db_session.query.return_value = mock_query

        retriever = ProjectRetriever(project_id=1)
        count = retriever.build_index(mock_db_session)

        assert count == 4
        assert retriever._is_fitted
        assert len(retriever.chunk_ids) == 4

    def test_retrieve_relevant_chunks(self, mock_db_session, sample_chunks):
        """Retrieves chunks relevant to query."""
        # Setup
        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = sample_chunks
        mock_db_session.query.return_value = mock_query

        retriever = ProjectRetriever(project_id=1)
        retriever.build_index(mock_db_session)

        # Query for user creation
        results = retriever.retrieve("create a new user", top_k=2)

        assert len(results) > 0
        # Should find createUser method as most relevant
        assert any("createUser" in r.content for r in results)

    def test_retrieve_auth_related(self, mock_db_session, sample_chunks):
        """Finds authentication-related chunks."""
        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = sample_chunks
        mock_db_session.query.return_value = mock_query

        retriever = ProjectRetriever(project_id=1)
        retriever.build_index(mock_db_session)

        results = retriever.retrieve("login authentication jwt", top_k=3)

        assert len(results) > 0
        # Should find auth-related chunks
        contents = " ".join(r.content for r in results)
        assert "authenticate" in contents or "useAuth" in contents

    def test_respects_token_budget(self, mock_db_session, sample_chunks):
        """Stops retrieving when token budget exhausted."""
        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = sample_chunks
        mock_db_session.query.return_value = mock_query

        retriever = ProjectRetriever(project_id=1)
        retriever.build_index(mock_db_session)

        # Very small budget
        results = retriever.retrieve("user", top_k=10, max_tokens=30)

        total_tokens = sum(r.token_count for r in results)
        assert total_tokens <= 30

    def test_empty_query_returns_empty(self, mock_db_session, sample_chunks):
        """Empty query returns no results."""
        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = sample_chunks
        mock_db_session.query.return_value = mock_query

        retriever = ProjectRetriever(project_id=1)
        retriever.build_index(mock_db_session)

        results = retriever.retrieve("")
        assert len(results) == 0

        results = retriever.retrieve("   ")
        assert len(results) == 0

    def test_unfitted_retriever_returns_empty(self):
        """Unfitted retriever returns empty results."""
        retriever = ProjectRetriever(project_id=1)
        results = retriever.retrieve("anything")
        assert len(results) == 0

    def test_no_chunks_returns_zero(self, mock_db_session):
        """Empty project returns zero chunks."""
        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query

        retriever = ProjectRetriever(project_id=1)
        count = retriever.build_index(mock_db_session)

        assert count == 0
        assert not retriever._is_fitted


class TestFormatContextForPrompt:
    """Tests for context formatting."""

    def test_empty_chunks(self):
        """Empty chunks return empty string."""
        result = format_context_for_prompt([])
        assert result == ""

    def test_single_chunk(self):
        """Formats single chunk correctly."""
        chunk = MagicMock()
        chunk.signature = "public void doSomething()"
        chunk.content = "// implementation"
        chunk.chunk_type = "method"

        retrieved = RetrievedChunk(
            chunk=chunk,
            file_path="Service.java",
            score=0.85,
            content="// implementation",
            token_count=10,
        )

        result = format_context_for_prompt([retrieved])

        assert "Service.java" in result
        assert "doSomething" in result
        assert "implementation" in result

    def test_multiple_chunks(self):
        """Formats multiple chunks with separation."""
        chunks = []
        for i in range(3):
            chunk = MagicMock()
            chunk.signature = f"method{i}()"
            chunk.content = f"// code {i}"
            chunk.chunk_type = "method"

            chunks.append(RetrievedChunk(
                chunk=chunk,
                file_path=f"File{i}.java",
                score=0.9 - i * 0.1,
                content=f"// code {i}",
                token_count=5,
            ))

        result = format_context_for_prompt(chunks)

        # All files should be mentioned
        assert "File0.java" in result
        assert "File1.java" in result
        assert "File2.java" in result

    def test_chunk_without_signature(self):
        """Handles chunks without signatures."""
        chunk = MagicMock()
        chunk.signature = None
        chunk.content = "some code content"
        chunk.chunk_type = "segment"

        retrieved = RetrievedChunk(
            chunk=chunk,
            file_path="script.py",
            score=0.5,
            content="some code content",
            token_count=8,
        )

        result = format_context_for_prompt([retrieved])

        assert "script.py" in result
        assert "some code content" in result


class TestCacheManagement:
    """Tests for retriever cache."""

    def test_clear_specific_project(self):
        """Clears cache for specific project."""
        from api.services.retriever import _retriever_cache

        # Add some cached retrievers
        _retriever_cache[1] = ProjectRetriever(1)
        _retriever_cache[2] = ProjectRetriever(2)

        clear_retriever_cache(project_id=1)

        assert 1 not in _retriever_cache
        assert 2 in _retriever_cache

        # Cleanup
        clear_retriever_cache()

    def test_clear_all(self):
        """Clears entire cache."""
        from api.services.retriever import _retriever_cache

        _retriever_cache[1] = ProjectRetriever(1)
        _retriever_cache[2] = ProjectRetriever(2)

        clear_retriever_cache()

        assert len(_retriever_cache) == 0


class TestRetrieveContextIntegration:
    """Integration tests for retrieve_context function."""

    def test_retrieve_context_creates_retriever(self):
        """retrieve_context creates and caches retriever."""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query

        # Clear cache first
        clear_retriever_cache()

        results = retrieve_context(mock_db, project_id=99, query="test")

        assert results == []  # No chunks, empty results

        # Cleanup
        clear_retriever_cache()
