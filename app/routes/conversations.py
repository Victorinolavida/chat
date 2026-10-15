from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from pydantic import ValidationError

from app.dtos.conversation_dto import ConversationCreateDTO, ConversationReadDTO
from app.responses import read_json_object, validation_error_response
from app.routes._helpers import current_user
from app.services.conversation_service import (
    InvalidParticipantsError,
    build_conversation_service,
)

conversations_bp = Blueprint(
    "conversations", __name__, url_prefix="/conversations"
)


@conversations_bp.get("")
@jwt_required()
def list_conversations():
    me = current_user()
    conversations = build_conversation_service().list_for_user(me)
    return jsonify(
        {
            "conversations": [
                ConversationReadDTO.from_model(conversation).model_dump(mode="json")
                for conversation in conversations
            ]
        }
    )


@conversations_bp.post("")
@jwt_required()
def create_conversation():
    body, error = read_json_object()
    if error is not None:
        return error

    try:
        payload = ConversationCreateDTO.model_validate(body)
    except ValidationError as validation_error:
        return validation_error_response(validation_error)

    me = current_user()
    try:
        conversation = build_conversation_service().create(me, payload.user_ids)
    except InvalidParticipantsError as invalid:
        return jsonify(
            {"error": "Invalid participants", "message": str(invalid)}
        ), 400

    return (
        jsonify(ConversationReadDTO.from_model(conversation).model_dump(mode="json")),
        201,
    )
