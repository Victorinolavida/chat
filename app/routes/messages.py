from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.dtos.message_dto import MessageReadDTO
from app.routes._helpers import current_user
from app.services.conversation_service import build_conversation_service
from app.services.message_service import build_message_service

messages_bp = Blueprint("messages", __name__, url_prefix="/messages")

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


@messages_bp.get("")
@jwt_required()
def list_messages():
    conversation_id = request.args.get("conversation_id") or None
    limit = request.args.get("limit", type=int) or DEFAULT_LIMIT
    limit = max(1, min(limit, MAX_LIMIT))

    service = build_message_service()
    if conversation_id is not None:
        me = current_user()
        conv_service = build_conversation_service()
        if not conv_service.is_member(conversation_id, me.id):
            return jsonify({"error": "Forbidden", "message": "Not a member of conversation"}), 403
        messages = service.list_by_conversation(conversation_id, limit=limit)
    else:
        messages = service.list_by_conversation(None, limit=limit)

    return jsonify(
        {
            "conversation_id": conversation_id,
            "messages": [
                MessageReadDTO.from_model(message).model_dump(mode="json")
                for message in messages
            ],
        }
    )
