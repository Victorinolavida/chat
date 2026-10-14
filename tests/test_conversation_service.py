import pytest

from app.extensions import db
from app.models.user import User
from app.services.conversation_service import (
    InvalidParticipantsError,
    build_conversation_service,
)


def _make_user(username, email):
    user = User(username=username, email=email, password_hash="hashed")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def users(app_context):
    return (
        _make_user("alice", "alice@example.com"),
        _make_user("bob", "bob@example.com"),
        _make_user("carol", "carol@example.com"),
    )


def test_create_includes_creator_and_participants(app_context, users):
    alice, bob, _ = users
    service = build_conversation_service()

    conversation = service.create(alice, [bob.id])

    assert set(conversation.member_ids()) == {alice.id, bob.id}
    assert conversation.created_at is not None


def test_create_is_idempotent_for_same_members(app_context, users):
    alice, bob, _ = users
    service = build_conversation_service()

    first = service.create(alice, [bob.id])
    second = service.create(bob, [alice.id])

    assert first.id == second.id
    assert db.session.query(type(first)).count() == 1


def test_create_rejects_unknown_participants(app_context, users):
    alice, _, _ = users
    service = build_conversation_service()

    with pytest.raises(InvalidParticipantsError):
        service.create(alice, [99999])


def test_is_member(app_context, users):
    alice, bob, carol = users
    service = build_conversation_service()
    conversation = service.create(alice, [bob.id])

    assert service.is_member(conversation.id, alice.id) is True
    assert service.is_member(conversation.id, carol.id) is False


def test_list_for_user_only_returns_their_conversations(app_context, users):
    alice, bob, carol = users
    service = build_conversation_service()
    first = service.create(alice, [bob.id])
    service.create(bob, [carol.id])

    alice_conversations = service.list_for_user(alice)

    assert [conversation.id for conversation in alice_conversations] == [first.id]
