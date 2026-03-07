"""Bridge Model API Server — main FastAPI application entry point.

Provides code generation inference via pluggable model backends,
authenticated with API keys and rate-limited per key.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.database import init_db
from api.routers import completions, keys, projects

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Code generation API powered by fine-tuned DeepSeek-Coder",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(completions.router)
app.include_router(keys.router)
app.include_router(projects.router)


@app.on_event("startup")
async def startup():
    """Initialize database tables on application startup."""
    logger.info("Starting %s", settings.app_name)
    init_db()


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return {"status": "healthy", "service": settings.app_name}
