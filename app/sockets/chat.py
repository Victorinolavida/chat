from datetime import datetime, timezone

from flask import request, session
from flask_jwt_extended import decode_token
from flask_socketio import ConnectionRefusedError, SocketIO, emit, join_room, leave_room
from pydantic import ValidationError

from app.dtos.message_dto import MessageCreateDTO, MessageReadDTO
from app.extensions import db
from app.models.user import User
from app.services.message_service import build_message_service

ROOM = "lobby"


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
        join_room(ROOM)
        emit(
            "chat:system",
            {
                "message": f"{user.username} joined the chat",
                "username": user.username,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            to=ROOM,
        )

    @socketio.on("chat:message")
    def handle_message(data):
        user_id = session.get("user_id")
        user = db.session.get(User, user_id) if user_id else None
        if user is None:
            raise ConnectionRefusedError("authentication required")

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

        message = build_message_service().create(user, payload.body)
        emit(
            "chat:message",
            MessageReadDTO.from_model(message).model_dump(mode="json"),
            to=ROOM,
        )

    @socketio.on("disconnect")
    def handle_disconnect():
        leave_room(ROOM, sid=request.sid)
