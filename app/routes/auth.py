from flask import Blueprint, jsonify
from flask_jwt_extended import create_access_token
from pydantic import ValidationError

from app.dtos.user_dto import UserCreateDTO, UserLoginDTO, UserReadDTO
from app.responses import read_json_object, validation_error_response
from app.services.user_service import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    build_user_service,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.post("/register")
def register():
    body, error = read_json_object()
    if error:
        return error

    try:
        data = UserCreateDTO.model_validate(body)
    except ValidationError as error:
        return validation_error_response(error)

    service = build_user_service()
    try:
        user = service.register(data)
    except UserAlreadyExistsError as error:
        return jsonify({"error": str(error), "field": error.field}), 409

    return jsonify(UserReadDTO.model_validate(user).model_dump(mode="json")), 201


@auth_bp.post("/login")
def login():
    body, error = read_json_object()
    if error:
        return error

    try:
        data = UserLoginDTO.model_validate(body)
    except ValidationError as error:
        return validation_error_response(error)

    service = build_user_service()
    try:
        user = service.authenticate(str(data.email), data.password)
    except InvalidCredentialsError as error:
        return jsonify({"error": str(error)}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify(
        {
            "access_token": token,
            "user": UserReadDTO.model_validate(user).model_dump(mode="json"),
        }
    )
