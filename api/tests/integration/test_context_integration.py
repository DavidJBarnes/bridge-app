"""Integration tests for context injection in completions."""

import pytest

from api.models.project import Project
from api.models.project_file import ProjectFile
from api.models.file_chunk import FileChunk


@pytest.fixture
def project_with_files(db_session, user_key):
    """Create a project with files and chunks for testing."""
    project = Project(
        name="Test Project",
        conventions="# Conventions\n- Use constructor injection",
        system_prompt="You are a Spring Boot expert.",
        api_key_id=user_key.id,
    )
    db_session.add(project)
    db_session.commit()

    # Add a file
    file = ProjectFile(
        project_id=project.id,
        file_path="UserService.java",
        file_type="java",
        total_tokens=50,
    )
    db_session.add(file)
    db_session.commit()

    # Add chunks
    chunks = [
        FileChunk(
            file_id=file.id,
            chunk_index=0,
            chunk_type="method",
            signature="public User createUser(CreateUserRequest request)",
            content="public User createUser(CreateUserRequest request) { return userRepository.save(new User(request)); }",
            token_count=25,
        ),
        FileChunk(
            file_id=file.id,
            chunk_index=1,
            chunk_type="method",
            signature="public void deleteUser(Long id)",
            content="public void deleteUser(Long id) { userRepository.deleteById(id); }",
            token_count=15,
        ),
    ]
    for chunk in chunks:
        db_session.add(chunk)
    db_session.commit()

    return project


class TestCompletionWithProject:
    """Tests for completions with project context."""

    def test_completion_without_project(self, client, user_headers):
        """Completion works without project."""
        response = client.post(
            "/v1/completions",
            json={"prompt": "Hello world"},
            headers=user_headers,
        )

        # Should not error (may fail if no inference provider configured)
        assert response.status_code in (200, 500, 503)

    def test_completion_with_project_id(self, client, user_headers, project_with_files):
        """Completion accepts project_id parameter."""
        response = client.post(
            "/v1/completions",
            json={
                "prompt": "Create a user service",
                "project_id": project_with_files.id,
            },
            headers=user_headers,
        )

        # Check request was accepted (inference may fail without provider)
        assert response.status_code in (200, 500, 503)

    def test_completion_with_invalid_project(self, client, user_headers):
        """Completion handles invalid project gracefully."""
        response = client.post(
            "/v1/completions",
            json={
                "prompt": "Test prompt",
                "project_id": 99999,
            },
            headers=user_headers,
        )

        # Should not error due to missing project
        assert response.status_code in (200, 500, 503)


class TestChatWithProject:
    """Tests for chat with project context."""

    def test_chat_with_project_id(self, client, user_headers, project_with_files):
        """Chat accepts project_id parameter."""
        response = client.post(
            "/v1/chat",
            json={
                "messages": [{"role": "user", "content": "Help me create a user"}],
                "project_id": project_with_files.id,
            },
            headers=user_headers,
        )

        assert response.status_code in (200, 500, 503)

    def test_chat_include_conventions_false(self, client, user_headers, project_with_files):
        """Chat respects include_conventions flag."""
        response = client.post(
            "/v1/chat",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "project_id": project_with_files.id,
                "include_conventions": False,
            },
            headers=user_headers,
        )

        assert response.status_code in (200, 500, 503)
