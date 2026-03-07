"""Tests for project management endpoints."""

import pytest

from api.models.project import Project
from api.models.project_file import ProjectFile
from api.models.file_chunk import FileChunk
from api.models.api_key import ApiKey


class TestCreateProject:
    """Tests for POST /v1/projects."""

    def test_create_project_success(self, client, user_headers):
        """Creates project with required fields."""
        response = client.post(
            "/v1/projects",
            json={"name": "My Project"},
            headers=user_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Project"
        assert data["id"] is not None
        assert data["file_count"] == 0
        assert data["total_chunks"] == 0

    def test_create_project_with_conventions(self, client, user_headers):
        """Creates project with conventions."""
        conventions = "# Conventions\n- Use 4 spaces\n- JavaDoc required"
        response = client.post(
            "/v1/projects",
            json={
                "name": "With Conventions",
                "conventions": conventions,
            },
            headers=user_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["conventions"] == conventions

    def test_create_project_with_system_prompt(self, client, user_headers):
        """Creates project with custom system prompt."""
        system_prompt = "You are a Spring Boot expert."
        response = client.post(
            "/v1/projects",
            json={
                "name": "With System Prompt",
                "system_prompt": system_prompt,
            },
            headers=user_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["system_prompt"] == system_prompt

    def test_create_project_empty_name_fails(self, client, user_headers):
        """Empty name is rejected."""
        response = client.post(
            "/v1/projects",
            json={"name": ""},
            headers=user_headers,
        )

        assert response.status_code == 422

    def test_create_project_unauthorized(self, client):
        """Request without auth is rejected."""
        response = client.post(
            "/v1/projects",
            json={"name": "Test"},
        )

        assert response.status_code in (401, 403)


class TestListProjects:
    """Tests for GET /v1/projects."""

    def test_list_empty(self, client, user_headers):
        """Returns empty list when no projects."""
        response = client.get("/v1/projects", headers=user_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["projects"] == []
        assert data["total"] == 0

    def test_list_projects(self, client, user_headers, db_session, user_key):
        """Returns all projects for API key."""
        for i in range(3):
            project = Project(name=f"Project {i}", api_key_id=user_key.id)
            db_session.add(project)
        db_session.commit()

        response = client.get("/v1/projects", headers=user_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["projects"]) == 3

    def test_list_projects_isolated(self, client, user_headers, db_session, user_key):
        """Only returns projects for authenticated key."""
        project1 = Project(name="Our Project", api_key_id=user_key.id)
        db_session.add(project1)

        other_key = ApiKey(name="other-key", key="other-key-value", is_admin=False, is_active=True)
        db_session.add(other_key)
        db_session.commit()

        project2 = Project(name="Other Project", api_key_id=other_key.id)
        db_session.add(project2)
        db_session.commit()

        response = client.get("/v1/projects", headers=user_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["projects"][0]["name"] == "Our Project"


class TestGetProject:
    """Tests for GET /v1/projects/{id}."""

    def test_get_project(self, client, user_headers, db_session, user_key):
        """Returns project details."""
        project = Project(
            name="Test Project",
            description="A test project",
            api_key_id=user_key.id,
        )
        db_session.add(project)
        db_session.commit()

        response = client.get(f"/v1/projects/{project.id}", headers=user_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["description"] == "A test project"

    def test_get_project_not_found(self, client, user_headers):
        """Returns 404 for missing project."""
        response = client.get("/v1/projects/99999", headers=user_headers)
        assert response.status_code == 404

    def test_get_other_key_project_fails(self, client, user_headers, db_session):
        """Cannot access another key's project."""
        other_key = ApiKey(name="other", key="other-value", is_admin=False, is_active=True)
        db_session.add(other_key)
        db_session.commit()

        project = Project(name="Other's Project", api_key_id=other_key.id)
        db_session.add(project)
        db_session.commit()

        response = client.get(f"/v1/projects/{project.id}", headers=user_headers)
        assert response.status_code == 404


class TestUpdateProject:
    """Tests for PUT /v1/projects/{id}."""

    def test_update_name(self, client, user_headers, db_session, user_key):
        """Updates project name."""
        project = Project(name="Old Name", api_key_id=user_key.id)
        db_session.add(project)
        db_session.commit()

        response = client.put(
            f"/v1/projects/{project.id}",
            json={"name": "New Name"},
            headers=user_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"

    def test_update_conventions(self, client, user_headers, db_session, user_key):
        """Updates project conventions."""
        project = Project(name="Project", api_key_id=user_key.id)
        db_session.add(project)
        db_session.commit()

        conventions = "# Updated Conventions\n- New rules"
        response = client.put(
            f"/v1/projects/{project.id}",
            json={"conventions": conventions},
            headers=user_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["conventions"] == conventions

    def test_partial_update(self, client, user_headers, db_session, user_key):
        """Partial update preserves other fields."""
        project = Project(
            name="Original",
            description="Original desc",
            conventions="Original conventions",
            api_key_id=user_key.id,
        )
        db_session.add(project)
        db_session.commit()

        response = client.put(
            f"/v1/projects/{project.id}",
            json={"name": "Updated"},
            headers=user_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated"
        assert data["description"] == "Original desc"
        assert data["conventions"] == "Original conventions"


class TestDeleteProject:
    """Tests for DELETE /v1/projects/{id}."""

    def test_delete_project(self, client, user_headers, db_session, user_key):
        """Deletes project."""
        project = Project(name="To Delete", api_key_id=user_key.id)
        db_session.add(project)
        db_session.commit()
        project_id = project.id

        response = client.delete(f"/v1/projects/{project_id}", headers=user_headers)

        assert response.status_code == 204

        # Verify deleted
        assert db_session.query(Project).filter_by(id=project_id).first() is None

    def test_delete_cascades_files(self, client, user_headers, db_session, user_key):
        """Deleting project cascades to files and chunks."""
        project = Project(name="With Files", api_key_id=user_key.id)
        db_session.add(project)
        db_session.commit()

        file = ProjectFile(project_id=project.id, file_path="test.java")
        db_session.add(file)
        db_session.commit()

        chunk = FileChunk(file_id=file.id, chunk_index=0, content="code")
        db_session.add(chunk)
        db_session.commit()

        file_id = file.id
        chunk_id = chunk.id

        response = client.delete(f"/v1/projects/{project.id}", headers=user_headers)
        assert response.status_code == 204

        # Verify cascade
        assert db_session.query(ProjectFile).filter_by(id=file_id).first() is None
        assert db_session.query(FileChunk).filter_by(id=chunk_id).first() is None


class TestUploadFile:
    """Tests for POST /v1/projects/{id}/files."""

    def test_upload_java_file(self, client, user_headers, db_session, user_key):
        """Uploads and chunks a Java file."""
        project = Project(name="Java Project", api_key_id=user_key.id)
        db_session.add(project)
        db_session.commit()

        java_code = """
public class UserService {
    public User findById(Long id) {
        return repository.findById(id).orElse(null);
    }
}
"""
        response = client.post(
            f"/v1/projects/{project.id}/files",
            data={"file_path": "UserService.java"},
            files={"file": ("UserService.java", java_code, "text/plain")},
            headers=user_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["file_path"] == "UserService.java"
        assert data["file_type"] == "java"
        assert data["chunk_count"] >= 1
        assert data["total_tokens"] > 0

    def test_upload_replaces_existing(self, client, user_headers, db_session, user_key):
        """Re-uploading same path replaces file."""
        project = Project(name="Project", api_key_id=user_key.id)
        db_session.add(project)
        db_session.commit()

        # First upload
        client.post(
            f"/v1/projects/{project.id}/files",
            data={"file_path": "test.java"},
            files={"file": ("test.java", "// version 1", "text/plain")},
            headers=user_headers,
        )

        # Second upload
        response = client.post(
            f"/v1/projects/{project.id}/files",
            data={"file_path": "test.java"},
            files={"file": ("test.java", "// version 2", "text/plain")},
            headers=user_headers,
        )

        assert response.status_code == 200

        # Should only have one file
        files = db_session.query(ProjectFile).filter_by(project_id=project.id).all()
        assert len(files) == 1


class TestUploadFileText:
    """Tests for POST /v1/projects/{id}/files/text."""

    def test_upload_text_content(self, client, user_headers, db_session, user_key):
        """Uploads file content as text."""
        project = Project(name="Project", api_key_id=user_key.id)
        db_session.add(project)
        db_session.commit()

        response = client.post(
            f"/v1/projects/{project.id}/files/text",
            data={
                "file_path": "config.py",
                "content": "DATABASE_URL = 'sqlite:///db.sqlite'"
            },
            headers=user_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["file_path"] == "config.py"
        assert data["file_type"] == "python"


class TestListFiles:
    """Tests for GET /v1/projects/{id}/files."""

    def test_list_files(self, client, user_headers, db_session, user_key):
        """Lists all files in project."""
        project = Project(name="Project", api_key_id=user_key.id)
        db_session.add(project)
        db_session.commit()

        for path in ["a.java", "b.java", "c.java"]:
            file = ProjectFile(project_id=project.id, file_path=path)
            db_session.add(file)
        db_session.commit()

        response = client.get(f"/v1/projects/{project.id}/files", headers=user_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3


class TestDeleteFile:
    """Tests for DELETE /v1/projects/{id}/files/{file_id}."""

    def test_delete_file(self, client, user_headers, db_session, user_key):
        """Deletes a file."""
        project = Project(name="Project", api_key_id=user_key.id)
        db_session.add(project)
        db_session.commit()

        file = ProjectFile(project_id=project.id, file_path="to_delete.java")
        db_session.add(file)
        db_session.commit()
        file_id = file.id

        response = client.delete(
            f"/v1/projects/{project.id}/files/{file_id}",
            headers=user_headers,
        )

        assert response.status_code == 204
        assert db_session.query(ProjectFile).filter_by(id=file_id).first() is None
