from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.routers.knowledge import router as knowledge_router
from app.routers.knowledge_relations import router as knowledge_relations_router
from app.routers.knowledge_revisions import router as knowledge_revisions_router
from app.routers.projects import router as projects_router


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API principale della piattaforma MRA Studio.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(knowledge_router)
app.include_router(knowledge_relations_router)
app.include_router(knowledge_revisions_router)
app.include_router(projects_router)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {
        "message": "MRA API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["system"])
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy: database unavailable.",
        ) from exc
    return {
        "status": "ok",
        "api": "ok",
        "database": "reachable",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/version", tags=["system"])
def version() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
    }
