from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.config import settings
from app.dependencies import get_auth_service, get_current_auth, require_csrf, require_login_origin
from app.schemas import AuthResponse, LoginRequest, UserRead
from app.services.auth_service import AuthContext, AuthPersistenceError, AuthService, InvalidCredentialsError

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


def _set_auth_cookies(response: Response, session_token: str, csrf_token: str) -> None:
    common = dict(secure=settings.session_cookie_secure, samesite=settings.session_cookie_samesite, path="/")
    response.set_cookie(settings.session_cookie_name, session_token, httponly=True, max_age=settings.session_absolute_ttl_seconds, **common)
    response.set_cookie(settings.csrf_cookie_name, csrf_token, httponly=False, max_age=settings.session_absolute_ttl_seconds, **common)


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/", secure=settings.session_cookie_secure, httponly=True, samesite=settings.session_cookie_samesite)
    response.delete_cookie(settings.csrf_cookie_name, path="/", secure=settings.session_cookie_secure, samesite=settings.session_cookie_samesite)


@router.post("/login", response_model=AuthResponse, dependencies=[Depends(require_login_origin)])
def login(payload: LoginRequest, response: Response, service: AuthService = Depends(get_auth_service)):
    try:
        user, session_token, csrf_token = service.login(payload.email, payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenziali non valide.") from exc
    except AuthPersistenceError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Impossibile completare l'accesso.") from exc
    _set_auth_cookies(response, session_token, csrf_token)
    return AuthResponse(user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def current_user(context: AuthContext = Depends(get_current_auth)):
    return context.user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)])
def logout(response: Response, context: AuthContext = Depends(get_current_auth), service: AuthService = Depends(get_auth_service)) -> None:
    try:
        service.logout(context)
    except AuthPersistenceError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Impossibile completare la disconnessione.") from exc
    _clear_auth_cookies(response)
