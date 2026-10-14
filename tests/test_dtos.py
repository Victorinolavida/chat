from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.dtos.user_dto import UserCreateDTO, UserLoginDTO, UserReadDTO
from app.models.user import User


def test_user_create_dto_accepts_valid_data():
    dto = UserCreateDTO(
        username="alice", email="alice@example.com", password="password123"
    )

    assert dto.username == "alice"
    assert dto.password == "password123"


def test_user_create_dto_normalizes_email():
    dto = UserCreateDTO(
        username="alice", email="alice@EXAMPLE.COM", password="password123"
    )

    assert str(dto.email) == "alice@example.com"


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "alice", "email": "not-an-email", "password": "password123"},
        {"username": "alice", "email": "alice@example.com", "password": "short"},
        {"username": "alice", "email": "alice@example.com", "password": "x" * 73},
        {"username": "ab", "email": "alice@example.com", "password": "password123"},
    ],
)
def test_user_create_dto_rejects_invalid_data(payload):
    with pytest.raises(ValidationError):
        UserCreateDTO.model_validate(payload)


def test_user_read_dto_from_user_excludes_password_hash():
    user = User(
        id=1,
        username="alice",
        email="alice@example.com",
        password_hash="$2b$12$fakehash",
        created_at=datetime.now(timezone.utc),
    )

    dto = UserReadDTO.model_validate(user)
    dumped = dto.model_dump()

    assert dto.id == 1
    assert dto.username == "alice"
    assert dto.email == "alice@example.com"
    assert "password_hash" not in dumped
    assert set(dumped.keys()) == {"id", "username", "email", "created_at"}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"email": "alice@example.com"},
        {"password": "password123"},
    ],
)
def test_user_login_dto_requires_email_and_password(payload):
    with pytest.raises(ValidationError):
        UserLoginDTO.model_validate(payload)


def test_user_login_dto_accepts_valid_data():
    dto = UserLoginDTO(email="alice@example.com", password="password123")

    assert str(dto.email) == "alice@example.com"
    assert dto.password == "password123"
