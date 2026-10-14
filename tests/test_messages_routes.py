from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models.user import User
from app.services.message_service import build_message_service


def _make_user(username="sender", email="sender@example.com"):
    user = User(username=username, email=email, password_hash="hashed")
    db.session.add(user)
    db.session.commit()
    return user


def _auth_header(user):
    token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}


def test_requires_authentication(client):
    response = client.get("/messages")

    assert response.status_code == 401


def test_returns_general_chat_when_conversation_id_is_absent(app_context, client):
    user = _make_user()
    service = build_message_service()
    service.create(user, "general one")
    service.create(user, "in a conversation", conversation_id="conv-1")

    response = client.get("/messages", headers=_auth_header(user))

    assert response.status_code == 200
    body = response.get_json()
    assert body["conversation_id"] is None
    assert [m["body"] for m in body["messages"]] == ["general one"]
    assert all(m["conversation_id"] is None for m in body["messages"])


def test_returns_messages_for_a_conversation(app_context, client):
    user = _make_user()
    service = build_message_service()
    service.create(user, "general one")
    conv_service = None
    from app.services.conversation_service import build_conversation_service

    conv_service = build_conversation_service()
    conversation = conv_service.create(user, [user.id])
    service.create(user, "hi there", conversation_id=conversation.id)

    response = client.get(
        f"/messages?conversation_id={conversation.id}", headers=_auth_header(user)
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["conversation_id"] == conversation.id
    assert [m["body"] for m in body["messages"]] == ["hi there"]

def test_messages_are_chronological(app_context, client):
    user = _make_user()
    service = build_message_service()
    for index in range(3):
        service.create(user, f"message {index}")

    response = client.get("/messages", headers=_auth_header(user))

    assert [m["body"] for m in response.get_json()["messages"]] == [
        "message 0",
        "message 1",
        "message 2",
    ]


def test_limit_is_respected(app_context, client):
    user = _make_user()
    service = build_message_service()
    for index in range(5):
        service.create(user, f"message {index}")

    response = client.get("/messages?limit=2", headers=_auth_header(user))

    assert [m["body"] for m in response.get_json()["messages"]] == [
        "message 3",
        "message 4",
    ]
