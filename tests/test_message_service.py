import uuid

from app.dtos.message_dto import MessageReadDTO
from app.extensions import db
from app.models.user import User
from app.services.message_service import build_message_service


def _make_user(username="sender", email="sender@example.com"):
    user = User(username=username, email=email, password_hash="hashed")
    db.session.add(user)
    db.session.commit()
    return user


def test_create_persists_message(app_context):
    user = _make_user()
    message = build_message_service().create(user, "hello world")

    assert message.body == "hello world"
    assert message.from_user_id == user.id
    assert message.conversation_id is None
    assert message.created_at is not None
    assert uuid.UUID(message.id).version == 7

    stored = db.session.get(type(message), message.id)
    assert stored is not None
    assert stored.body == "hello world"
    assert stored.from_user.username == "sender"


def test_create_in_conversation(app_context):
    sender = _make_user()
    message = build_message_service().create(sender, "hi there", conversation_id="conv-1")

    assert message.conversation_id == "conv-1"
    assert message.from_user_id == sender.id

def test_list_recent_is_chronological(app_context):
    user = _make_user()
    service = build_message_service()
    for index in range(3):
        service.create(user, f"message {index}")

    messages = service.list_recent()

    assert [m.body for m in messages] == ["message 0", "message 1", "message 2"]


def test_list_recent_respects_limit(app_context):
    user = _make_user()
    service = build_message_service()
    for index in range(5):
        service.create(user, f"message {index}")

    messages = service.list_recent(limit=2)

    assert [m.body for m in messages] == ["message 3", "message 4"]


def test_read_dto_serializes_created_at_as_utc(app_context):
    user = _make_user()
    message = build_message_service().create(user, "hello")

    payload = MessageReadDTO.from_model(message).model_dump(mode="json")

    assert payload["created_at"].endswith(("Z", "+00:00"))
    assert payload["from_username"] == "sender"
