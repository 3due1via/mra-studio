import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_auth_service, require_admin, require_csrf
from app.schemas import UserCreate, UserRead, UserUpdate
from app.services.auth_service import AuthPersistenceError, AuthService, LastAdminError, UserConflictError, UserNotFoundError

router = APIRouter(prefix="/api/v1/users", tags=["users"], dependencies=[Depends(require_admin)])


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, UserNotFoundError): return HTTPException(status_code=404, detail="Utente non trovato.")
    if isinstance(exc, UserConflictError): return HTTPException(status_code=409, detail="Email già registrata.")
    if isinstance(exc, LastAdminError): return HTTPException(status_code=409, detail="Deve rimanere almeno un amministratore attivo.")
    return HTTPException(status_code=500, detail="Impossibile salvare l'utente.")


@router.get("", response_model=list[UserRead])
def list_users(service: AuthService = Depends(get_auth_service)): return service.list_users()


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_csrf)])
def create_user(payload: UserCreate, service: AuthService = Depends(get_auth_service)):
    try: return service.create_user(payload)
    except (UserConflictError, AuthPersistenceError) as exc: raise _translate(exc) from exc


@router.patch("/{user_id}", response_model=UserRead, dependencies=[Depends(require_csrf)])
def update_user(user_id: uuid.UUID, payload: UserUpdate, service: AuthService = Depends(get_auth_service)):
    try: return service.update_user(user_id, payload)
    except (UserNotFoundError, LastAdminError, AuthPersistenceError) as exc: raise _translate(exc) from exc


@router.post("/{user_id}/revoke-sessions", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)])
def revoke_sessions(user_id: uuid.UUID, service: AuthService = Depends(get_auth_service)) -> None:
    try: service.revoke_user_sessions(user_id)
    except UserNotFoundError as exc: raise _translate(exc) from exc
