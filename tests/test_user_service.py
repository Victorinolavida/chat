import pytest

from app.dtos.user_dto import UserCreateDTO
from app.services.user_service import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    build_user_service,
)


@pytest.fixture
def service():
    return build_user_service()


def make_dto(username="alice", email="alice@example.com", password="password123"):
    return UserCreateDTO(username=username, email=email, password=password)


def test_hash_password_differs_from_plaintext(service):
    plaintext = "s3cretpassword"
    hashed = service._hash_password(plaintext)

    assert hashed != plaintext
    assert plaintext not in hashed
    assert hashed.startswith("$2")


def test_verify_password_correct_and_wrong(service):
    plaintext = "s3cretpassword"
    hashed = service._hash_password(plaintext)

    assert service._verify_password(plaintext, hashed) is True
    assert service._verify_password("wrongpassword", hashed) is False


def test_register_creates_user_with_hashed_password(app_context, service):
    user = service.register(make_dto())

    assert user.id is not None
    assert user.username == "alice"
    assert user.email == "alice@example.com"
    assert user.password_hash != "password123"
    assert user.password_hash.startswith("$2")
    assert user.created_at is not None


def test_register_duplicate_email_raises(app_context, service):
    service.register(make_dto())

    with pytest.raises(UserAlreadyExistsError) as exc_info:
        service.register(make_dto(username="alice2"))

    assert exc_info.value.field == "email"


def test_register_duplicate_username_raises(app_context, service):
    service.register(make_dto())

    with pytest.raises(UserAlreadyExistsError) as exc_info:
        service.register(make_dto(email="other@example.com"))

    assert exc_info.value.field == "username"


def test_authenticate_returns_user_on_valid_credentials(app_context, service):
    created = service.register(make_dto())

    user = service.authenticate("alice@example.com", "password123")

    assert user.id == created.id


def test_authenticate_raises_on_wrong_password(app_context, service):
    service.register(make_dto())

    with pytest.raises(InvalidCredentialsError):
        service.authenticate("alice@example.com", "wrongpassword")


def test_authenticate_raises_on_unknown_email(app_context, service):
    with pytest.raises(InvalidCredentialsError):
        service.authenticate("nobody@example.com", "password123")


def test_get_by_email_and_username(app_context, service):
    created = service.register(make_dto())

    assert service.get_by_email("alice@example.com").id == created.id
    assert service.get_by_username("alice").id == created.id
    assert service.get_by_email("missing@example.com") is None
    assert service.get_by_username("missing") is None
