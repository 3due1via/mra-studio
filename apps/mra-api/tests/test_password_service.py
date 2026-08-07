from app.services.password_service import PasswordService


def test_argon2_hash_does_not_store_plaintext():
    service = PasswordService()
    password = "A-secure-password-123"
    password_hash = service.hash(password)
    assert password not in password_hash
    assert password_hash.startswith("$argon2id$")
    assert service.verify(password_hash, password)


def test_wrong_or_malformed_password_hash_is_rejected():
    service = PasswordService()
    assert not service.verify(service.hash("correct-password-123"), "wrong-password")
    assert not service.verify("not-an-argon2-hash", "wrong-password")
