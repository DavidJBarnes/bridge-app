"""Tests for project memory database models."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.models.api_key import ApiKey, Base
from api.models.project import Project
from api.models.project_file import ProjectFile
from api.models.file_chunk import FileChunk


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def api_key(db_session):
    """Create a test API key."""
    key = ApiKey(name="test-key", key="test-key-value", is_admin=False)
    db_session.add(key)
    db_session.commit()
    return key


class TestProjectModel:
    """Tests for the Project model."""

    def test_create_project(self, db_session, api_key):
        """Project can be created with required fields."""
        project = Project(
            name="My Project",
            api_key_id=api_key.id,
        )
        db_session.add(project)
        db_session.commit()

        assert project.id is not None
        assert project.name == "My Project"
        assert project.api_key_id == api_key.id
        assert project.created_at is not None

    def test_project_with_conventions(self, db_session, api_key):
        """Project stores conventions text."""
        conventions = "# Coding Standards\n- Use 4 spaces\n- JavaDoc on all public methods"
        project = Project(
            name="With Conventions",
            conventions=conventions,
            api_key_id=api_key.id,
        )
        db_session.add(project)
        db_session.commit()

        retrieved = db_session.query(Project).filter_by(id=project.id).first()
        assert retrieved.conventions == conventions

    def test_project_with_system_prompt(self, db_session, api_key):
        """Project stores custom system prompt."""
        system_prompt = "You are a Spring Boot expert. Always use constructor injection."
        project = Project(
            name="With System Prompt",
            system_prompt=system_prompt,
            api_key_id=api_key.id,
        )
        db_session.add(project)
        db_session.commit()

        retrieved = db_session.query(Project).filter_by(id=project.id).first()
        assert retrieved.system_prompt == system_prompt

    def test_project_with_description(self, db_session, api_key):
        """Project stores optional description."""
        project = Project(
            name="Described Project",
            description="A Spring Boot microservice for user management.",
            api_key_id=api_key.id,
        )
        db_session.add(project)
        db_session.commit()

        retrieved = db_session.query(Project).filter_by(id=project.id).first()
        assert retrieved.description == "A Spring Boot microservice for user management."

    def test_project_cascade_delete(self, db_session, api_key):
        """Deleting project cascades to files and chunks."""
        project = Project(name="Cascade Test", api_key_id=api_key.id)
        db_session.add(project)
        db_session.commit()

        file = ProjectFile(project_id=project.id, file_path="test.java")
        db_session.add(file)
        db_session.commit()

        chunk = FileChunk(file_id=file.id, chunk_index=0, content="public class Test {}")
        db_session.add(chunk)
        db_session.commit()

        db_session.delete(project)
        db_session.commit()

        assert db_session.query(ProjectFile).filter_by(id=file.id).first() is None
        assert db_session.query(FileChunk).filter_by(id=chunk.id).first() is None

    def test_project_updated_at(self, db_session, api_key):
        """Project updated_at is set on creation."""
        project = Project(name="Timestamp Test", api_key_id=api_key.id)
        db_session.add(project)
        db_session.commit()

        assert project.updated_at is not None
        assert project.created_at is not None


class TestProjectFileModel:
    """Tests for the ProjectFile model."""

    def test_create_project_file(self, db_session, api_key):
        """ProjectFile can be created with required fields."""
        project = Project(name="Test Project", api_key_id=api_key.id)
        db_session.add(project)
        db_session.commit()

        file = ProjectFile(
            project_id=project.id,
            file_path="src/main/java/UserService.java",
            file_type="java",
        )
        db_session.add(file)
        db_session.commit()

        assert file.id is not None
        assert file.file_path == "src/main/java/UserService.java"
        assert file.file_type == "java"

    def test_project_file_with_summary(self, db_session, api_key):
        """ProjectFile stores summary text."""
        project = Project(name="Test Project", api_key_id=api_key.id)
        db_session.add(project)
        db_session.commit()

        file = ProjectFile(
            project_id=project.id,
            file_path="UserService.java",
            summary="Service layer for user CRUD operations with password encoding.",
            total_tokens=250,
        )
        db_session.add(file)
        db_session.commit()

        retrieved = db_session.query(ProjectFile).filter_by(id=file.id).first()
        assert retrieved.summary == "Service layer for user CRUD operations with password encoding."
        assert retrieved.total_tokens == 250

    def test_project_file_default_tokens(self, db_session, api_key):
        """ProjectFile defaults to 0 tokens."""
        project = Project(name="Test Project", api_key_id=api_key.id)
        db_session.add(project)
        db_session.commit()

        file = ProjectFile(project_id=project.id, file_path="Empty.java")
        db_session.add(file)
        db_session.commit()

        assert file.total_tokens == 0

    def test_file_cascade_delete_chunks(self, db_session, api_key):
        """Deleting a file cascades to its chunks."""
        project = Project(name="Test Project", api_key_id=api_key.id)
        db_session.add(project)
        db_session.commit()

        file = ProjectFile(project_id=project.id, file_path="Test.java")
        db_session.add(file)
        db_session.commit()

        chunk = FileChunk(file_id=file.id, chunk_index=0, content="code")
        db_session.add(chunk)
        db_session.commit()
        chunk_id = chunk.id

        db_session.delete(file)
        db_session.commit()

        assert db_session.query(FileChunk).filter_by(id=chunk_id).first() is None


class TestFileChunkModel:
    """Tests for the FileChunk model."""

    def test_create_file_chunk(self, db_session, api_key):
        """FileChunk can be created with required fields."""
        project = Project(name="Test Project", api_key_id=api_key.id)
        db_session.add(project)
        db_session.commit()

        file = ProjectFile(project_id=project.id, file_path="Test.java")
        db_session.add(file)
        db_session.commit()

        chunk = FileChunk(
            file_id=file.id,
            chunk_index=0,
            chunk_type="function",
            signature="public User createUser(CreateUserRequest request)",
            content="public User createUser(CreateUserRequest request) {\n    // implementation\n}",
            token_count=45,
            start_line=10,
            end_line=25,
        )
        db_session.add(chunk)
        db_session.commit()

        assert chunk.id is not None
        assert chunk.chunk_type == "function"
        assert chunk.signature == "public User createUser(CreateUserRequest request)"
        assert chunk.token_count == 45
        assert chunk.start_line == 10
        assert chunk.end_line == 25

    def test_multiple_chunks_per_file(self, db_session, api_key):
        """A file can have multiple ordered chunks."""
        project = Project(name="Test Project", api_key_id=api_key.id)
        db_session.add(project)
        db_session.commit()

        file = ProjectFile(project_id=project.id, file_path="MultiMethod.java")
        db_session.add(file)
        db_session.commit()

        for i in range(3):
            chunk = FileChunk(
                file_id=file.id,
                chunk_index=i,
                content=f"// Method {i}",
            )
            db_session.add(chunk)
        db_session.commit()

        chunks = db_session.query(FileChunk).filter_by(file_id=file.id).order_by(FileChunk.chunk_index).all()
        assert len(chunks) == 3
        assert [c.chunk_index for c in chunks] == [0, 1, 2]

    def test_chunk_default_type(self, db_session, api_key):
        """FileChunk defaults to 'segment' type."""
        project = Project(name="Test Project", api_key_id=api_key.id)
        db_session.add(project)
        db_session.commit()

        file = ProjectFile(project_id=project.id, file_path="Test.java")
        db_session.add(file)
        db_session.commit()

        chunk = FileChunk(file_id=file.id, chunk_index=0, content="some code")
        db_session.add(chunk)
        db_session.commit()

        assert chunk.chunk_type == "segment"
        assert chunk.token_count == 0

    def test_chunk_nullable_fields(self, db_session, api_key):
        """FileChunk allows null signature, start_line, end_line."""
        project = Project(name="Test Project", api_key_id=api_key.id)
        db_session.add(project)
        db_session.commit()

        file = ProjectFile(project_id=project.id, file_path="Test.java")
        db_session.add(file)
        db_session.commit()

        chunk = FileChunk(file_id=file.id, chunk_index=0, content="code")
        db_session.add(chunk)
        db_session.commit()

        assert chunk.signature is None
        assert chunk.start_line is None
        assert chunk.end_line is None


class TestApiKeyProjectRelationship:
    """Tests for ApiKey <-> Project relationship."""

    def test_api_key_has_projects(self, db_session, api_key):
        """ApiKey.projects returns associated projects."""
        project1 = Project(name="Project 1", api_key_id=api_key.id)
        project2 = Project(name="Project 2", api_key_id=api_key.id)
        db_session.add_all([project1, project2])
        db_session.commit()

        db_session.refresh(api_key)
        assert len(api_key.projects) == 2

    def test_delete_api_key_cascades_to_projects(self, db_session):
        """Deleting API key cascades to projects."""
        key = ApiKey(name="temp-key", key="temp-key-value", is_admin=False)
        db_session.add(key)
        db_session.commit()

        project = Project(name="Temp Project", api_key_id=key.id)
        db_session.add(project)
        db_session.commit()

        project_id = project.id
        db_session.delete(key)
        db_session.commit()

        assert db_session.query(Project).filter_by(id=project_id).first() is None

    def test_project_references_api_key(self, db_session, api_key):
        """Project.api_key navigates back to the owning key."""
        project = Project(name="Nav Test", api_key_id=api_key.id)
        db_session.add(project)
        db_session.commit()

        db_session.refresh(project)
        assert project.api_key.id == api_key.id
        assert project.api_key.name == "test-key"


class TestRelationshipNavigation:
    """Tests for navigating the full Project -> File -> Chunk chain."""

    def test_project_files_navigation(self, db_session, api_key):
        """Project.files returns associated files."""
        project = Project(name="Nav Test", api_key_id=api_key.id)
        db_session.add(project)
        db_session.commit()

        f1 = ProjectFile(project_id=project.id, file_path="A.java", file_type="java")
        f2 = ProjectFile(project_id=project.id, file_path="B.ts", file_type="typescript")
        db_session.add_all([f1, f2])
        db_session.commit()

        db_session.refresh(project)
        assert len(project.files) == 2
        paths = {f.file_path for f in project.files}
        assert paths == {"A.java", "B.ts"}

    def test_file_chunks_navigation(self, db_session, api_key):
        """ProjectFile.chunks returns associated chunks."""
        project = Project(name="Nav Test", api_key_id=api_key.id)
        db_session.add(project)
        db_session.commit()

        file = ProjectFile(project_id=project.id, file_path="Test.java")
        db_session.add(file)
        db_session.commit()

        for i in range(5):
            db_session.add(FileChunk(file_id=file.id, chunk_index=i, content=f"chunk {i}"))
        db_session.commit()

        db_session.refresh(file)
        assert len(file.chunks) == 5

    def test_chunk_file_navigation(self, db_session, api_key):
        """FileChunk.file navigates back to parent file."""
        project = Project(name="Nav Test", api_key_id=api_key.id)
        db_session.add(project)
        db_session.commit()

        file = ProjectFile(project_id=project.id, file_path="Parent.java")
        db_session.add(file)
        db_session.commit()

        chunk = FileChunk(file_id=file.id, chunk_index=0, content="code")
        db_session.add(chunk)
        db_session.commit()

        db_session.refresh(chunk)
        assert chunk.file.file_path == "Parent.java"

    def test_file_project_navigation(self, db_session, api_key):
        """ProjectFile.project navigates back to parent project."""
        project = Project(name="Parent Project", api_key_id=api_key.id)
        db_session.add(project)
        db_session.commit()

        file = ProjectFile(project_id=project.id, file_path="Child.java")
        db_session.add(file)
        db_session.commit()

        db_session.refresh(file)
        assert file.project.name == "Parent Project"
