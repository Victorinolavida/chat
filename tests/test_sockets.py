from flask_jwt_extended import create_access_token

from app.extensions import db, socketio
from app.models.message import Message
from app.models.user import User


def _make_user(username="sender", email="sender@example.com"):
    user = User(username=username, email=email, password_hash="hashed")
    db.session.add(user)
    db.session.commit()
    return user


def _token(user):
    return create_access_token(identity=str(user.id))


def _of(events, name):
    return [event for event in events if event["name"] == name]


def test_connect_without_token_is_refused(app_context):
    client = socketio.test_client(app_context)

    assert client.is_connected() is False


def test_connect_with_invalid_token_is_refused(app_context):
    client = socketio.test_client(app_context, auth={"token": "not-a-jwt"})

    assert client.is_connected() is False


def test_connect_with_valid_token_succeeds(app_context):
    user = _make_user()
    client = socketio.test_client(app_context, auth={"token": _token(user)})

    assert client.is_connected() is True
    assert len(_of(client.get_received(), "chat:system")) == 1


def test_sending_message_persists_and_broadcasts(app_context):
    user = _make_user()
    client = socketio.test_client(app_context, auth={"token": _token(user)})
    client.get_received()

    client.emit("chat:message", {"message": "hello world"})

    events = _of(client.get_received(), "chat:message")
    assert len(events) == 1
    payload = events[0]["args"][0]
    assert payload["body"] == "hello world"
    assert payload["from_username"] == "sender"
    assert payload["from_user_id"] == user.id
    assert payload["conversation_id"] is None
    assert db.session.query(Message).count() == 1


def test_message_is_broadcast_to_other_clients(app_context):
    sender = _make_user(username="sender", email="sender@example.com")
    receiver = _make_user(username="receiver", email="receiver@example.com")
    sender_client = socketio.test_client(app_context, auth={"token": _token(sender)})
    receiver_client = socketio.test_client(app_context, auth={"token": _token(receiver)})
    sender_client.get_received()
    receiver_client.get_received()

    sender_client.emit("chat:message", {"message": "hey receiver"})

    events = _of(receiver_client.get_received(), "chat:message")
    assert len(events) == 1
    assert events[0]["args"][0]["body"] == "hey receiver"


def test_empty_message_is_rejected(app_context):
    user = _make_user()
    client = socketio.test_client(app_context, auth={"token": _token(user)})
    client.get_received()

    client.emit("chat:message", {"message": "   "})

    events = client.get_received()
    assert len(_of(events, "chat:message")) == 0
    errors = _of(events, "chat:error")
    assert len(errors) == 1
    assert "empty" in errors[0]["args"][0]["message"].lower()
    assert db.session.query(Message).count() == 0


def test_whitespace_is_trimmed(app_context):
    user = _make_user()
    client = socketio.test_client(app_context, auth={"token": _token(user)})
    client.get_received()

    client.emit("chat:message", {"message": "  hi  "})

    payload = _of(client.get_received(), "chat:message")[0]["args"][0]
    assert payload["body"] == "hi"


def test_private_message_is_isolated_to_members(app_context):
    from app.services.conversation_service import build_conversation_service

    alice = _make_user(username="alice", email="alice@example.com")
    bob = _make_user(username="bob", email="bob@example.com")
    carol = _make_user(username="carol", email="carol@example.com")

    conversation = build_conversation_service().create(alice, [bob.id])

    alice_client = socketio.test_client(app_context, auth={"token": _token(alice)})
    bob_client = socketio.test_client(app_context, auth={"token": _token(bob)})
    carol_client = socketio.test_client(app_context, auth={"token": _token(carol)})
    for client in (alice_client, bob_client, carol_client):
        client.get_received()

    alice_client.emit(
        "chat:message",
        {
            "message": "secret",
            "conversation_id": conversation.id,
            "to_user_id": bob.id,
            "private": True,
        },
    )

    assert len(_of(alice_client.get_received(), "chat:message")) == 1
    bob_events = _of(bob_client.get_received(), "chat:message")
    assert len(bob_events) == 1
    assert bob_events[0]["args"][0]["conversation_id"] == conversation.id
    assert len(_of(carol_client.get_received(), "chat:message")) == 0
    assert all(
        message.conversation_id == conversation.id
        for message in db.session.query(Message).all()
    )


def test_non_member_cannot_send_to_conversation(app_context):
    from app.services.conversation_service import build_conversation_service

    alice = _make_user(username="alice", email="alice@example.com")
    bob = _make_user(username="bob", email="bob@example.com")
    carol = _make_user(username="carol", email="carol@example.com")

    conversation = build_conversation_service().create(alice, [bob.id])

    carol_client = socketio.test_client(app_context, auth={"token": _token(carol)})
    carol_client.get_received()

    carol_client.emit(
        "chat:message", {"message": "intruder", "conversation_id": conversation.id}
    )

    events = carol_client.get_received()
    assert len(_of(events, "chat:message")) == 0
    assert len(_of(events, "chat:error")) == 1
    assert db.session.query(Message).count() == 0
