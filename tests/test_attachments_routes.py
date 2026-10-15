from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models.user import User
from app.services.conversation_service import build_conversation_service


def _make_user(username="uploader", email="uploader@example.com"):
    user = User(username=username, email=email, password_hash="hashed")
    db.session.add(user)
    db.session.commit()
    return user


def _auth_header(user):
    token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}


def _make_conversation(*users):
    creator, *others = users
    return build_conversation_service().create(
        creator, [user.id for user in others]
    )


def test_requires_authentication(client):
    response = client.post("/attachments", json={"filename": "a.txt"})

    assert response.status_code == 401


def test_create_upload_returns_presigned_url(app_context, client):
    user = _make_user()

    response = client.post(
        "/attachments",
        headers=_auth_header(user),
        json={
            "filename": "holiday photo.png",
            "content_type": "image/png",
            "size_bytes": 1234,
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["id"]
    assert body["filename"] == "holiday photo.png"
    assert body["content_type"] == "image/png"
    assert body["size_bytes"] == 1234
    assert body["conversation_id"] is None
    assert body["object_key"].startswith("general/attachments/")
    assert body["object_key"].endswith("holiday_photo.png")
    assert body["upload_url"].startswith("http://localhost:9000/")
    assert body["upload_url"].split("?")[0].endswith(body["object_key"])


def test_create_upload_rejects_empty_filename(app_context, client):
    user = _make_user()

    response = client.post(
        "/attachments",
        headers=_auth_header(user),
        json={"filename": "   "},
    )

    assert response.status_code == 422


def test_create_upload_requires_conversation_membership(app_context, client):
    member = _make_user("member", "member@example.com")
    outsider = _make_user("outsider", "outsider@example.com")
    conversation = _make_conversation(member, _make_user("friend", "friend@example.com"))

    response = client.post(
        "/attachments",
        headers=_auth_header(outsider),
        json={"filename": "secret.pdf", "conversation_id": conversation.id},
    )

    assert response.status_code == 403


def test_create_upload_scopes_key_to_conversation(app_context, client):
    user = _make_user()
    partner = _make_user("partner", "partner@example.com")
    conversation = _make_conversation(user, partner)

    response = client.post(
        "/attachments",
        headers=_auth_header(user),
        json={"filename": "notes.txt", "conversation_id": conversation.id},
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["conversation_id"] == conversation.id
    assert body["object_key"].startswith(
        f"conversations/{conversation.id}/attachments/"
    )


def test_download_url_for_owner(app_context, client):
    user = _make_user()
    created = client.post(
        "/attachments",
        headers=_auth_header(user),
        json={"filename": "a.txt"},
    ).get_json()

    response = client.get(f"/attachments/{created['id']}", headers=_auth_header(user))

    assert response.status_code == 200
    body = response.get_json()
    assert body["id"] == created["id"]
    assert body["download_url"].startswith("http://localhost:9000/")


def test_download_requires_authentication(app_context, client):
    user = _make_user()
    created = client.post(
        "/attachments", headers=_auth_header(user), json={"filename": "a.txt"}
    ).get_json()

    response = client.get(f"/attachments/{created['id']}")

    assert response.status_code == 401


def test_download_forbidden_for_non_member(app_context, client):
    owner = _make_user("owner", "owner@example.com")
    partner = _make_user("partner", "partner@example.com")
    outsider = _make_user("outsider", "outsider@example.com")
    conversation = _make_conversation(owner, partner)
    created = client.post(
        "/attachments",
        headers=_auth_header(owner),
        json={"filename": "notes.txt", "conversation_id": conversation.id},
    ).get_json()

    response = client.get(
        f"/attachments/{created['id']}", headers=_auth_header(outsider)
    )

    assert response.status_code == 403


def test_download_missing_returns_404(app_context, client):
    user = _make_user()

    response = client.get("/attachments/does-not-exist", headers=_auth_header(user))

    assert response.status_code == 404


def test_list_scopes_to_conversation(app_context, client):
    owner = _make_user("owner", "owner@example.com")
    partner = _make_user("partner", "partner@example.com")
    conversation = _make_conversation(owner, partner)

    client.post(
        "/attachments", headers=_auth_header(owner), json={"filename": "general.txt"}
    )
    client.post(
        "/attachments",
        headers=_auth_header(owner),
        json={"filename": "shared.txt", "conversation_id": conversation.id},
    )

    response = client.get(
        f"/attachments?conversation_id={conversation.id}",
        headers=_auth_header(partner),
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["conversation_id"] == conversation.id
    assert [attachment["filename"] for attachment in body["attachments"]] == [
        "shared.txt"
    ]
