from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token
from pydantic import ValidationError

from app.dtos.user_dto import UserCreateDTO, UserLoginDTO, UserReadDTO
from app.services.user_service import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    build_user_service,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _validation_error(error: ValidationError):
    return jsonify({"error": "Validation error", "details": error.errors()}), 422


@auth_bp.post("/register")
def register():
    try:
        data = UserCreateDTO.model_validate(request.get_json(silent=True) or {})
    except ValidationError as error:
        return _validation_error(error)

    service = build_user_service()
    try:
        user = service.register(data)
    except UserAlreadyExistsError as error:
        return jsonify({"error": str(error), "field": error.field}), 409

    return jsonify(UserReadDTO.model_validate(user).model_dump(mode="json")), 201


@auth_bp.post("/login")
def login():
    try:
        data = UserLoginDTO.model_validate(request.get_json(silent=True) or {})
    except ValidationError as error:
        return _validation_error(error)

    service = build_user_service()
    try:
        user = service.authenticate(str(data.email), data.password)
    except InvalidCredentialsError as error:
        return jsonify({"error": str(error)}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": token, "user": UserReadDTO.model_validate(user).model_dump(mode="json")})
