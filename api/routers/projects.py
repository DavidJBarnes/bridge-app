"""Project management endpoints for context memory.

Provides CRUD operations for projects, file uploads, and context
configuration. All projects are scoped to the authenticated API key.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.database import get_db
from api.dependencies import get_current_api_key
from api.models.api_key import ApiKey
from api.models.project import Project
from api.models.project_file import ProjectFile
from api.models.file_chunk import FileChunk
from api.services.chunker import chunk_file, detect_file_type
from api.services.retriever import clear_retriever_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/projects", tags=["projects"])


# --- Request/Response Models ---

class CreateProjectRequest(BaseModel):
    """Request to create a new project."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    conventions: str | None = None
    system_prompt: str | None = None


class UpdateProjectRequest(BaseModel):
    """Request to update project settings."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    conventions: str | None = None
    system_prompt: str | None = None


class ProjectResponse(BaseModel):
    """Project details response."""
    id: int
    name: str
    description: str | None
    conventions: str | None
    system_prompt: str | None
    file_count: int
    total_chunks: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """List of projects response."""
    projects: list[ProjectResponse]
    total: int


class FileUploadResponse(BaseModel):
    """Response after uploading a file."""
    file_id: int
    file_path: str
    file_type: str | None
    chunk_count: int
    total_tokens: int


class ProjectFileResponse(BaseModel):
    """Project file details."""
    id: int
    file_path: str
    file_type: str | None
    summary: str | None
    total_tokens: int
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectFilesListResponse(BaseModel):
    """List of files in a project."""
    files: list[ProjectFileResponse]
    total: int


# --- Helper Functions ---

def _get_project_or_404(
    db: Session,
    project_id: int,
    api_key: ApiKey,
) -> Project:
    """Get a project by ID, ensuring it belongs to the API key.

    Args:
        db: Database session.
        project_id: The project ID.
        api_key: The authenticated API key.

    Returns:
        The Project instance.

    Raises:
        HTTPException: If project not found or not owned by key.
    """
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.api_key_id == api_key.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _count_project_stats(db: Session, project_id: int) -> tuple[int, int]:
    """Count files and chunks for a project.

    Args:
        db: Database session.
        project_id: The project ID.

    Returns:
        Tuple of (file_count, chunk_count).
    """
    file_count = db.query(ProjectFile).filter(ProjectFile.project_id == project_id).count()
    chunk_count = (
        db.query(FileChunk)
        .join(ProjectFile)
        .filter(ProjectFile.project_id == project_id)
        .count()
    )
    return file_count, chunk_count


def _project_to_response(db: Session, project: Project) -> ProjectResponse:
    """Convert a Project model to response format.

    Args:
        db: Database session.
        project: The Project instance.

    Returns:
        ProjectResponse with computed stats.
    """
    file_count, chunk_count = _count_project_stats(db, project.id)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        conventions=project.conventions,
        system_prompt=project.system_prompt,
        file_count=file_count,
        total_chunks=chunk_count,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


# --- Project CRUD Endpoints ---

@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    request: CreateProjectRequest,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Create a new project for storing code context.

    Projects organize files and conventions for context injection
    during code generation requests.
    """
    project = Project(
        name=request.name,
        description=request.description,
        conventions=request.conventions,
        system_prompt=request.system_prompt,
        api_key_id=api_key.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    logger.info("Created project '%s' (id=%d) for key '%s'", project.name, project.id, api_key.name)
    return _project_to_response(db, project)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """List all projects belonging to the authenticated API key."""
    projects = (
        db.query(Project)
        .filter(Project.api_key_id == api_key.id)
        .order_by(Project.updated_at.desc())
        .all()
    )

    return ProjectListResponse(
        projects=[_project_to_response(db, p) for p in projects],
        total=len(projects),
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Get details of a specific project."""
    project = _get_project_or_404(db, project_id, api_key)
    return _project_to_response(db, project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    request: UpdateProjectRequest,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Update project settings.

    Only provided fields are updated; omitted fields remain unchanged.
    """
    project = _get_project_or_404(db, project_id, api_key)

    if request.name is not None:
        project.name = request.name
    if request.description is not None:
        project.description = request.description
    if request.conventions is not None:
        project.conventions = request.conventions
    if request.system_prompt is not None:
        project.system_prompt = request.system_prompt

    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)

    logger.info("Updated project '%s' (id=%d)", project.name, project.id)
    return _project_to_response(db, project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Delete a project and all its files and chunks.

    This action is irreversible.
    """
    project = _get_project_or_404(db, project_id, api_key)

    project_name = project.name
    db.delete(project)
    db.commit()

    # Clear retriever cache for this project
    clear_retriever_cache(project_id)

    logger.info("Deleted project '%s' (id=%d)", project_name, project_id)


# --- File Management Endpoints ---

@router.post("/{project_id}/files", response_model=FileUploadResponse)
async def upload_file(
    project_id: int,
    file: UploadFile = File(...),
    file_path: str = Form(..., description="Relative path for the file, e.g. 'src/UserService.java'"),
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Upload a source file to the project.

    The file is parsed and split into chunks for retrieval.
    If a file with the same path exists, it is replaced.
    """
    project = _get_project_or_404(db, project_id, api_key)

    # Read file content
    content = await file.read()
    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text")

    # Delete existing file with same path
    existing = (
        db.query(ProjectFile)
        .filter(ProjectFile.project_id == project_id, ProjectFile.file_path == file_path)
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()

    # Detect file type
    file_type = detect_file_type(file_path)

    # Create file record
    project_file = ProjectFile(
        project_id=project_id,
        file_path=file_path,
        file_type=file_type,
    )
    db.add(project_file)
    db.commit()
    db.refresh(project_file)

    # Parse and create chunks
    total_tokens = 0
    chunk_count = 0

    for i, chunk in enumerate(chunk_file(text_content, file_path)):
        file_chunk = FileChunk(
            file_id=project_file.id,
            chunk_index=i,
            chunk_type=chunk.chunk_type,
            signature=chunk.signature,
            content=chunk.content,
            token_count=chunk.token_count,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
        )
        db.add(file_chunk)
        total_tokens += chunk.token_count
        chunk_count += 1

    # Update file stats
    project_file.total_tokens = total_tokens
    db.commit()

    # Invalidate retriever cache
    clear_retriever_cache(project_id)

    logger.info(
        "Uploaded file '%s' to project %d: %d chunks, %d tokens",
        file_path, project_id, chunk_count, total_tokens,
    )

    return FileUploadResponse(
        file_id=project_file.id,
        file_path=file_path,
        file_type=file_type,
        chunk_count=chunk_count,
        total_tokens=total_tokens,
    )


@router.post("/{project_id}/files/text", response_model=FileUploadResponse)
async def upload_file_text(
    project_id: int,
    file_path: str = Form(..., description="Relative path for the file"),
    content: str = Form(..., description="File content as text"),
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Upload file content directly as text.

    Alternative to file upload when content is already available as a string.
    Useful for programmatic uploads or testing.
    """
    project = _get_project_or_404(db, project_id, api_key)

    # Delete existing file with same path
    existing = (
        db.query(ProjectFile)
        .filter(ProjectFile.project_id == project_id, ProjectFile.file_path == file_path)
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()

    # Detect file type
    file_type = detect_file_type(file_path)

    # Create file record
    project_file = ProjectFile(
        project_id=project_id,
        file_path=file_path,
        file_type=file_type,
    )
    db.add(project_file)
    db.commit()
    db.refresh(project_file)

    # Parse and create chunks
    total_tokens = 0
    chunk_count = 0

    for i, chunk in enumerate(chunk_file(content, file_path)):
        file_chunk = FileChunk(
            file_id=project_file.id,
            chunk_index=i,
            chunk_type=chunk.chunk_type,
            signature=chunk.signature,
            content=chunk.content,
            token_count=chunk.token_count,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
        )
        db.add(file_chunk)
        total_tokens += chunk.token_count
        chunk_count += 1

    project_file.total_tokens = total_tokens
    db.commit()

    clear_retriever_cache(project_id)

    logger.info(
        "Uploaded text file '%s' to project %d: %d chunks, %d tokens",
        file_path, project_id, chunk_count, total_tokens,
    )

    return FileUploadResponse(
        file_id=project_file.id,
        file_path=file_path,
        file_type=file_type,
        chunk_count=chunk_count,
        total_tokens=total_tokens,
    )


@router.get("/{project_id}/files", response_model=ProjectFilesListResponse)
async def list_project_files(
    project_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """List all files in a project."""
    project = _get_project_or_404(db, project_id, api_key)

    files = (
        db.query(ProjectFile)
        .filter(ProjectFile.project_id == project_id)
        .order_by(ProjectFile.file_path)
        .all()
    )

    file_responses = []
    for f in files:
        chunk_count = db.query(FileChunk).filter(FileChunk.file_id == f.id).count()
        file_responses.append(ProjectFileResponse(
            id=f.id,
            file_path=f.file_path,
            file_type=f.file_type,
            summary=f.summary,
            total_tokens=f.total_tokens,
            chunk_count=chunk_count,
            created_at=f.created_at,
            updated_at=f.updated_at,
        ))

    return ProjectFilesListResponse(
        files=file_responses,
        total=len(file_responses),
    )


@router.get("/{project_id}/files/{file_id}", response_model=ProjectFileResponse)
async def get_project_file(
    project_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Get details of a specific file."""
    project = _get_project_or_404(db, project_id, api_key)

    file = (
        db.query(ProjectFile)
        .filter(ProjectFile.id == file_id, ProjectFile.project_id == project_id)
        .first()
    )
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    chunk_count = db.query(FileChunk).filter(FileChunk.file_id == file.id).count()

    return ProjectFileResponse(
        id=file.id,
        file_path=file.file_path,
        file_type=file.file_type,
        summary=file.summary,
        total_tokens=file.total_tokens,
        chunk_count=chunk_count,
        created_at=file.created_at,
        updated_at=file.updated_at,
    )


@router.delete("/{project_id}/files/{file_id}", status_code=204)
async def delete_project_file(
    project_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Delete a file from the project."""
    project = _get_project_or_404(db, project_id, api_key)

    file = (
        db.query(ProjectFile)
        .filter(ProjectFile.id == file_id, ProjectFile.project_id == project_id)
        .first()
    )
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = file.file_path
    db.delete(file)
    db.commit()

    clear_retriever_cache(project_id)

    logger.info("Deleted file '%s' from project %d", file_path, project_id)
