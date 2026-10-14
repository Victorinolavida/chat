import pytest
from pydantic import ValidationError

from app.dtos.user_dto import UserCreateDTO
from app.responses import read_json_object, validation_error_response


def test_read_json_object_missing_content_type(app):
    with app.test_request_context("/auth/register", method="POST", data="hello"):
        body, error = read_json_object()

    assert body is None
    response, status = error
    assert status == 415
    assert response.get_json()["error"] == "Unsupported content type"


def test_read_json_object_malformed_json(app):
    with app.test_request_context(
        "/auth/register",
        method="POST",
        data="{not valid json",
        content_type="application/json",
    ):
        body, error = read_json_object()

    assert body is None
    response, status = error
    assert status == 400
    assert response.get_json()["error"] == "Malformed JSON"


def test_read_json_object_rejects_json_array(app):
    with app.test_request_context(
        "/auth/register", method="POST", json=[1, 2, 3]
    ):
        body, error = read_json_object()

    assert body is None
    response, status = error
    assert status == 400
    assert response.get_json()["error"] == "Invalid payload"


def test_read_json_object_returns_dict(app):
    with app.test_request_context(
        "/auth/register", method="POST", json={"username": "alice"}
    ):
        body, error = read_json_object()

    assert error is None
    assert body == {"username": "alice"}


def test_validation_error_response_shape_and_message(app):
    with app.test_request_context("/auth/register", method="POST"):
        with pytest.raises(ValidationError) as exc_info:
            UserCreateDTO.model_validate(
                {
                    "username": "ab",
                    "email": "alice@example.com",
                    "password": "password123",
                }
            )
        response, status = validation_error_response(exc_info.value)

    assert status == 422
    payload = response.get_json()
    assert set(payload.keys()) == {"error", "message"}
    assert "details" not in payload
    assert "username" in payload["message"]
