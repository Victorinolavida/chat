from flask_jwt_extended import create_access_token

from app.extensions import db
from app.media import MAX_UPLOAD_BYTES
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


def _create(client, user, **overrides):
    payload = {"filename": "a.txt", "size_bytes": 10}
    payload.update(overrides)
    return client.post("/attachments", headers=_auth_header(user), json=payload)


def test_requires_authentication(client):
    response = client.post("/attachments", json={"filename": "a.txt", "size_bytes": 1})

    assert response.status_code == 401


def test_create_upload_returns_presigned_post(app_context, client):
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
    assert body["extension"] == "png"
    assert body["category"] == "image"
    assert body["size_bytes"] == 1234
    assert body["human_size"] == "1.2 KB"
    assert body["conversation_id"] is None
    assert body["object_key"].startswith("general_conversation/attachments/")
    assert body["object_key"].endswith("holiday_photo.png")
    assert body["upload_url"].startswith("http://localhost:9000/")
    assert body["upload_fields"]["Content-Type"] == "image/png"
    assert body["upload_fields"]["policy"]
    assert body["max_size_bytes"] == MAX_UPLOAD_BYTES


def test_create_upload_normalizes_content_type(app_context, client):
    user = _make_user()

    response = _create(client, user, filename="track.MP3", size_bytes=2048)

    assert response.status_code == 201
    body = response.get_json()
    assert body["extension"] == "mp3"
    assert body["category"] == "audio"
    assert body["content_type"] == "audio/mpeg"
    assert body["object_key"].endswith("track.mp3")


def test_create_upload_rejects_unsupported_format(app_context, client):
    user = _make_user()

    response = _create(client, user, filename="malware.exe", size_bytes=10)

    assert response.status_code == 422


def test_create_upload_rejects_mismatched_content_type(app_context, client):
    user = _make_user()

    response = _create(
        client,
        user,
        filename="photo.png",
        content_type="application/pdf",
        size_bytes=10,
    )

    assert response.status_code == 422


def test_create_upload_rejects_empty_filename(app_context, client):
    user = _make_user()

    response = _create(client, user, filename="   ")

    assert response.status_code == 422


def test_create_upload_rejects_oversized_file(app_context, client):
    user = _make_user()

    response = _create(client, user, size_bytes=MAX_UPLOAD_BYTES + 1)

    assert response.status_code == 422


def test_create_upload_requires_positive_size(app_context, client):
    user = _make_user()

    response = _create(client, user, size_bytes=0)

    assert response.status_code == 422


def test_create_upload_requires_conversation_membership(app_context, client):
    member = _make_user("member", "member@example.com")
    outsider = _make_user("outsider", "outsider@example.com")
    conversation = _make_conversation(member, _make_user("friend", "friend@example.com"))

    response = _create(
        client,
        outsider,
        filename="secret.pdf",
        size_bytes=10,
        conversation_id=conversation.id,
    )

    assert response.status_code == 403


def test_create_upload_scopes_key_to_conversation(app_context, client):
    user = _make_user()
    partner = _make_user("partner", "partner@example.com")
    conversation = _make_conversation(user, partner)

    response = _create(
        client, user, filename="notes.txt", size_bytes=10,
        conversation_id=conversation.id,
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["conversation_id"] == conversation.id
    assert body["object_key"].startswith(
        f"conversations/{conversation.id}/attachments/"
    )


def test_download_url_for_owner(app_context, client):
    user = _make_user()
    created = _create(client, user).get_json()

    response = client.get(f"/attachments/{created['id']}", headers=_auth_header(user))

    assert response.status_code == 200
    body = response.get_json()
    assert body["id"] == created["id"]
    assert body["extension"] == "txt"
    assert body["category"] == "text"
    assert body["download_url"].startswith("http://localhost:9000/")


def test_download_requires_authentication(app_context, client):
    user = _make_user()
    created = _create(client, user).get_json()

    response = client.get(f"/attachments/{created['id']}")

    assert response.status_code == 401


def test_download_forbidden_for_non_member(app_context, client):
    owner = _make_user("owner", "owner@example.com")
    partner = _make_user("partner", "partner@example.com")
    outsider = _make_user("outsider", "outsider@example.com")
    conversation = _make_conversation(owner, partner)
    created = _create(
        client, owner, filename="notes.txt", size_bytes=10,
        conversation_id=conversation.id,
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

    _create(client, owner, filename="general.txt")
    _create(
        client, owner, filename="shared.txt", size_bytes=10,
        conversation_id=conversation.id,
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
