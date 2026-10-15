import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db, socketio
from app.models.attachment import Attachment
from app.models.message import Message
from app.models.user import User
from app.services.attachment_service import build_attachment_service
from app.services.conversation_service import build_conversation_service
from app.services.message_service import InvalidAttachmentError, build_message_service


def _make_user(username="sender", email="sender@example.com"):
    user = User(username=username, email=email, password_hash="hashed")
    db.session.add(user)
    db.session.commit()
    return user


def _token(user):
    return create_access_token(identity=str(user.id))


def _of(events, name):
    return [event for event in events if event["name"] == name]


def _attachment(user, filename="notes.txt", conversation_id=None, size=10):
    attachment, _ = build_attachment_service().create_upload(
        uploader=user,
        filename=filename,
        size_bytes=size,
        conversation_id=conversation_id,
    )
    return attachment


def test_message_links_attachments(app_context):
    user = _make_user()
    attachment = _attachment(user, filename="notes.txt")

    message = build_message_service().create(
        user, "", attachment_ids=[attachment.id]
    )

    assert message.attachments == [attachment]
    assert attachment.message_id == message.id


def test_message_links_multiple_attachments_in_order(app_context):
    user = _make_user()
    first = _attachment(user, filename="a.txt")
    second = _attachment(user, filename="cover.png")

    message = build_message_service().create(
        user, "look", attachment_ids=[first.id, second.id]
    )

    assert [a.filename for a in message.attachments] == ["a.txt", "cover.png"]


def test_unknown_attachment_is_rejected(app_context):
    user = _make_user()

    with pytest.raises(InvalidAttachmentError):
        build_message_service().create(user, "hi", attachment_ids=["missing"])

    assert db.session.query(Message).count() == 0


def test_attachment_from_another_user_is_rejected(app_context):
    owner = _make_user("owner", "owner@example.com")
    intruder = _make_user("intruder", "intruder@example.com")
    attachment = _attachment(owner)

    with pytest.raises(InvalidAttachmentError):
        build_message_service().create(
            intruder, "steal", attachment_ids=[attachment.id]
        )

    assert attachment.message_id is None


def test_attachment_conversation_must_match(app_context):
    user = _make_user()
    partner = _make_user("partner", "partner@example.com")
    conversation = build_conversation_service().create(user, [partner.id])
    attachment = _attachment(user, conversation_id=conversation.id)

    with pytest.raises(InvalidAttachmentError):
        build_message_service().create(user, "wrong place", attachment_ids=[attachment.id])


def test_attachment_cannot_be_reused(app_context):
    user = _make_user()
    attachment = _attachment(user)
    build_message_service().create(user, "first", attachment_ids=[attachment.id])

    with pytest.raises(InvalidAttachmentError):
        build_message_service().create(user, "second", attachment_ids=[attachment.id])


def test_message_read_dto_includes_attachment_url(app_context):
    from app.dtos.message_dto import MessageReadDTO

    user = _make_user()
    attachment = _attachment(user, filename="photo.png")
    message = build_message_service().create(
        user, "", attachment_ids=[attachment.id]
    )

    payload = MessageReadDTO.from_model(message).model_dump(mode="json")

    assert payload["body"] == ""
    assert len(payload["attachments"]) == 1
    item = payload["attachments"][0]
    assert item["id"] == attachment.id
    assert item["filename"] == "photo.png"
    assert item["category"] == "image"
    assert item["download_url"].startswith("http://localhost:9000/")


def test_delete_for_message_removes_rows_and_objects(app_context, monkeypatch):
    removed = []

    class FakeStorage:
        def delete(self, key):
            removed.append(key)

    user = _make_user()
    attachment = _attachment(user)
    message = build_message_service().create(
        user, "", attachment_ids=[attachment.id]
    )

    monkeypatch.setattr(
        "app.services.attachment_service.build_storage_service",
        lambda: FakeStorage(),
    )

    count = build_attachment_service().delete_for_message(message.id)

    assert count == 1
    assert removed == [attachment.object_key]
    assert db.session.get(Attachment, attachment.id) is None


def test_socket_message_with_attachment(app_context):
    user = _make_user()
    attachment = _attachment(user, filename="report.json")
    client = socketio.test_client(app_context, auth={"token": _token(user)})
    client.get_received()

    client.emit(
        "chat:message",
        {"message": "", "attachment_ids": [attachment.id]},
    )

    events = _of(client.get_received(), "chat:message")
    assert len(events) == 1
    payload = events[0]["args"][0]
    assert payload["body"] == ""
    assert [a["filename"] for a in payload["attachments"]] == ["report.json"]
    assert db.session.query(Message).count() == 1


def test_socket_rejects_foreign_attachment(app_context):
    owner = _make_user("owner", "owner@example.com")
    intruder = _make_user("intruder", "intruder@example.com")
    attachment = _attachment(owner)
    client = socketio.test_client(app_context, auth={"token": _token(intruder)})
    client.get_received()

    client.emit(
        "chat:message",
        {"message": "", "attachment_ids": [attachment.id]},
    )

    events = client.get_received()
    assert len(_of(events, "chat:message")) == 0
    errors = _of(events, "chat:error")
    assert len(errors) == 1
    assert "another user" in errors[0]["args"][0]["message"].lower()
