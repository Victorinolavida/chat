import uuid

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
    assert message.to_user_id is None
    assert message.created_at is not None
    assert uuid.UUID(message.id).version == 7

    stored = db.session.get(type(message), message.id)
    assert stored is not None
    assert stored.body == "hello world"
    assert stored.from_user.username == "sender"


def test_create_with_recipient(app_context):
    sender = _make_user()
    recipient = _make_user(username="recipient", email="r@example.com")

    message = build_message_service().create(sender, "hi there", to_user=recipient)

    assert message.to_user_id == recipient.id


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
