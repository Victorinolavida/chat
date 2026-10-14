from datetime import datetime, timezone

from flask import request, session
from flask_jwt_extended import decode_token
from flask_socketio import ConnectionRefusedError, SocketIO, emit, join_room, leave_room
from pydantic import ValidationError

from app import presence
from app.dtos.message_dto import MessageCreateDTO, MessageReadDTO
from app.extensions import db
from app.models.user import User
from app.services.conversation_service import build_conversation_service
from app.services.message_service import build_message_service

ROOM_LOBBY = "lobby"
ROOM_CONVERSATION = "conversation:{id}"


def _user_from_token(token: str | None) -> User | None:
    if not token:
        return None
    try:
        claims = decode_token(token)
    except Exception:
        return None
    user_id = claims.get("sub")
    if user_id is None:
        return None
    return db.session.get(User, int(user_id))


def _message_validation_error(error: ValidationError) -> str:
    details = {
        ".".join(str(part) for part in err["loc"]) or "message": err["msg"]
        for err in error.errors()
    }
    return "; ".join(f"{field}: {msg}" for field, msg in details.items())


def register_chat_events(socketio: SocketIO) -> None:
    @socketio.on("connect")
    def handle_connect(auth):
        user = _user_from_token((auth or {}).get("token"))
        if user is None:
            raise ConnectionRefusedError("authentication failed")

        session["user_id"] = user.id
        join_room(ROOM_LOBBY)
        presence.add(request.sid, user.id)

        emit(
            "chat:system",
            {
                "message": f"{user.username} joined the chat",
                "username": user.username,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            to=ROOM_LOBBY,
        )
        emit("presence:update", {"user_id": user.id, "online": True}, broadcast=True)

        conv_service = build_conversation_service()
        for conversation in conv_service.list_for_user(user):
            join_room(ROOM_CONVERSATION.format(id=conversation.id))

    @socketio.on("chat:message")
    def handle_message(data):
        user_id = session.get("user_id")
        user = db.session.get(User, user_id) if user_id else None
        if user is None:
            raise ConnectionRefusedError("authentication required")

        data = data or {}
        conversation_id = data.get("conversation_id") or None

        try:
            payload = MessageCreateDTO.model_validate(
                {"body": (data or {}).get("message", "")}
            )
        except ValidationError as error:
            emit(
                "chat:error",
                {"error": "Validation error", "message": _message_validation_error(error)},
                to=request.sid,
            )
            return

        conv_service = build_conversation_service()
        if conversation_id is not None:
            if not conv_service.is_member(conversation_id, user.id):
                emit(
                    "chat:error",
                    {"error": "Forbidden", "message": "Not a member of conversation"},
                    to=request.sid,
                )
                return
            to_user_id = data.get("to_user_id")
            if to_user_id is not None:
                try:
                    to_user_id_int = int(to_user_id)
                except (TypeError, ValueError):
                    emit(
                        "chat:error",
                        {"error": "Validation error", "message": "Invalid to_user_id"},
                        to=request.sid,
                    )
                    return
                if not conv_service.is_member(conversation_id, to_user_id_int):
                    emit(
                        "chat:error",
                        {"error": "Validation error", "message": "Recipient not in conversation"},
                        to=request.sid,
                    )
                    return

        message = build_message_service().create(user, payload.body, conversation_id)

        if conversation_id is not None:
            emit(
                "chat:message",
                MessageReadDTO.from_model(message).model_dump(mode="json"),
                to=ROOM_CONVERSATION.format(id=conversation_id),
            )
            return

        emit(
            "chat:message",
            MessageReadDTO.from_model(message).model_dump(mode="json"),
            to=ROOM_LOBBY,
        )

    @socketio.on("disconnect")
    def handle_disconnect():
        user_id = session.get("user_id")
        presence.remove(request.sid)
        leave_room(ROOM_LOBBY, sid=request.sid)
        if user_id:
            emit("presence:update", {"user_id": user_id, "online": False}, broadcast=True)
