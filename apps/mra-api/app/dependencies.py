import hmac

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories.knowledge_relation_repository import (
    SqlAlchemyKnowledgeRelationRepository,
)
from app.repositories.knowledge_repository import SqlAlchemyKnowledgeRepository
from app.repositories.knowledge_revision_repository import (
    SqlAlchemyKnowledgeRevisionRepository,
)
from app.repositories.workspace_repository import SqlAlchemyWorkspaceRepository
from app.services.knowledge_relation_service import KnowledgeRelationService
from app.services.knowledge_revision_service import KnowledgeRevisionService
from app.services.knowledge_service import KnowledgeService
from app.services.workspace_service import WorkspaceService
from app.repositories.intervention_repository import SqlAlchemyInterventionRepository
from app.services.intervention_service import InterventionService
from app.repositories.auth_repository import SqlAlchemyAuthRepository
from app.services.auth_service import AuthenticationError, AuthContext, AuthService, token_hash
from app.services.password_service import PasswordService
from app.config import settings
from app.browser_security import validate_browser_request
from app.audit_context import get_request_audit_context
from app.repositories.audit_repository import SqlAlchemyAuditRepository
from app.services.audit_service import AuditService

password_service = PasswordService()


def get_audit_service(
    request: Request,
    db: Session = Depends(get_db),
) -> AuditService:
    return AuditService(SqlAlchemyAuditRepository(db), get_request_audit_context(request))


def get_knowledge_revision_service_from_db(db: Session, audit: AuditService | None = None) -> KnowledgeRevisionService:
    return KnowledgeRevisionService(
        SqlAlchemyKnowledgeRevisionRepository(db),
        SqlAlchemyKnowledgeRepository(db),
        audit,
    )


def get_knowledge_service(db: Session = Depends(get_db), audit: AuditService = Depends(get_audit_service)) -> KnowledgeService:
    revision_service = get_knowledge_revision_service_from_db(db, audit)
    return KnowledgeService(
        SqlAlchemyKnowledgeRepository(db),
        revision_service=revision_service,
        audit=audit,
    )


def get_knowledge_relation_service(
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> KnowledgeRelationService:
    knowledge_repository = SqlAlchemyKnowledgeRepository(db)
    return KnowledgeRelationService(
        SqlAlchemyKnowledgeRelationRepository(db),
        knowledge_repository,
        audit,
    )


def get_knowledge_revision_service(
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> KnowledgeRevisionService:
    return get_knowledge_revision_service_from_db(db, audit)


def get_workspace_service(db: Session = Depends(get_db), audit: AuditService = Depends(get_audit_service)) -> WorkspaceService:
    return WorkspaceService(SqlAlchemyWorkspaceRepository(db), audit)


def get_intervention_service(db: Session = Depends(get_db), audit: AuditService = Depends(get_audit_service)) -> InterventionService:
    return InterventionService(SqlAlchemyInterventionRepository(db), audit)


def get_auth_service(db: Session = Depends(get_db), audit: AuditService = Depends(get_audit_service)) -> AuthService:
    return AuthService(SqlAlchemyAuthRepository(db), password_service, audit)


def get_current_auth(
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> AuthContext:
    try:
        context = service.authenticate(request.cookies.get(settings.session_cookie_name))
        get_request_audit_context(request).set_actor(context.user.id, context.user.email)
        return context
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticazione richiesta.") from exc


def require_viewer(context: AuthContext = Depends(get_current_auth)):
    return context.user


def require_editor(context: AuthContext = Depends(get_current_auth)):
    if context.user.role not in {"admin", "editor"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permessi insufficienti.")
    return context.user


def require_admin(context: AuthContext = Depends(get_current_auth)):
    if context.user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permessi insufficienti.")
    return context.user


def require_csrf(
    request: Request,
    context: AuthContext = Depends(get_current_auth),
    csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    validate_browser_request(request)
    if not csrf_token or not hmac.compare_digest(token_hash(csrf_token), context.session.csrf_token_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token CSRF non valido.")


def require_login_origin(request: Request) -> None:
    validate_browser_request(request)
