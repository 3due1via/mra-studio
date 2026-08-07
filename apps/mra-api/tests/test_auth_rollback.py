from unittest.mock import Mock
from types import SimpleNamespace

import pytest

from app.schemas import UserCreate
from app.services.auth_service import AuthContext, AuthPersistenceError, AuthService
from app.services.password_service import PasswordService


def test_create_user_rolls_back_unexpected_persistence_error():
    repository = Mock()
    repository.get_user_by_email.return_value = None
    repository.commit.side_effect = RuntimeError("forced failure")
    service = AuthService(repository, PasswordService())
    with pytest.raises(AuthPersistenceError):
        service.create_user(UserCreate(email="rollback@example.test", display_name="Rollback", password="A-secure-password-123", role="viewer"))
    repository.rollback.assert_called_once()


def test_logout_rolls_back_unexpected_persistence_error():
    repository = Mock()
    repository.commit.side_effect = RuntimeError("forced failure")
    service = AuthService(repository, PasswordService())
    session = SimpleNamespace(revoked_at=None)
    context = AuthContext(user=SimpleNamespace(), session=session)
    with pytest.raises(AuthPersistenceError):
        service.logout(context)
    repository.rollback.assert_called_once()
