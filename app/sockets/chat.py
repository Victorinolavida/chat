from datetime import datetime, timezone

from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room

ROOM = "lobby"


def register_chat_events(socketio: SocketIO) -> None:
    @socketio.on("connect")
    def handle_connect(auth):
        username = (auth or {}).get("username", "anonymous")
        join_room(ROOM)
        emit(
            "system",
            {
                "message": f"{username} joined the chat",
                "username": username,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            to=ROOM,
        )

    @socketio.on("message")
    def handle_message(data):
        payload = {
            "username": data.get("username", "anonymous"),
            "message": data.get("message", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        emit("message", payload, to=ROOM)

    @socketio.on("disconnect")
    def handle_disconnect():
        sid = request.sid
        leave_room(ROOM, sid=sid)
