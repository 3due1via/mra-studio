from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.routers.knowledge import router as knowledge_router
from app.routers.knowledge_relations import router as knowledge_relations_router
from app.routers.knowledge_revisions import router as knowledge_revisions_router
from app.routers.environments import router as environments_router
from app.routers.objects import router as objects_router
from app.routers.projects import router as projects_router
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.audit_context import bind_audit_context, create_audit_context, reset_audit_context
from app.routers.audit import router as audit_router
from app.routers.interventions import router as interventions_router
from app.services.audit_service import AuditUnavailableError


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API principale della piattaforma MRA Studio.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "X-CSRF-Token"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    context = create_audit_context()
    request.state.audit_context = context
    token = bind_audit_context(context)
    try:
        try:
            response = await call_next(request)
        except Exception:
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Errore interno del servizio."},
            )
        response.headers["X-Request-ID"] = str(context.request_id)
        return response
    finally:
        reset_audit_context(token)
        request.state.audit_context = None

app.include_router(knowledge_router)
app.include_router(knowledge_relations_router)
app.include_router(knowledge_revisions_router)
app.include_router(projects_router)
app.include_router(environments_router)
app.include_router(objects_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(audit_router)
app.include_router(interventions_router)


@app.exception_handler(AuditUnavailableError)
async def audit_unavailable_handler(_request: Request, _exc: AuditUnavailableError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Servizio temporaneamente non disponibile."},
    )


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
