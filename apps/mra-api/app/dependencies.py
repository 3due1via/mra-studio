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
from app.repositories.auth_repository import SqlAlchemyAuthRepository
from app.services.auth_service import AuthenticationError, AuthContext, AuthService, token_hash
from app.services.password_service import PasswordService
from app.config import settings
from app.browser_security import validate_browser_request

password_service = PasswordService()


def get_knowledge_revision_service_from_db(db: Session) -> KnowledgeRevisionService:
    return KnowledgeRevisionService(
        SqlAlchemyKnowledgeRevisionRepository(db),
        SqlAlchemyKnowledgeRepository(db),
    )


def get_knowledge_service(db: Session = Depends(get_db)) -> KnowledgeService:
    revision_service = get_knowledge_revision_service_from_db(db)
    return KnowledgeService(
        SqlAlchemyKnowledgeRepository(db),
        revision_service=revision_service,
    )


def get_knowledge_relation_service(
    db: Session = Depends(get_db),
) -> KnowledgeRelationService:
    knowledge_repository = SqlAlchemyKnowledgeRepository(db)
    return KnowledgeRelationService(
        SqlAlchemyKnowledgeRelationRepository(db),
        knowledge_repository,
    )


def get_knowledge_revision_service(
    db: Session = Depends(get_db),
) -> KnowledgeRevisionService:
    return get_knowledge_revision_service_from_db(db)


def get_workspace_service(db: Session = Depends(get_db)) -> WorkspaceService:
    return WorkspaceService(SqlAlchemyWorkspaceRepository(db))


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(SqlAlchemyAuthRepository(db), password_service)


def get_current_auth(
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> AuthContext:
    try:
        return service.authenticate(request.cookies.get(settings.session_cookie_name))
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
