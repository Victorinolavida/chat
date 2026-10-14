from app.extensions import db
from app.models.conversation import Conversation, ConversationMember
from app.models.user import User


class ConversationNotFoundError(Exception):
    pass


class InvalidParticipantsError(Exception):
    pass


class ConversationService:
    def get(self, conversation_id: str) -> Conversation | None:
        return db.session.get(Conversation, conversation_id)

    def is_member(self, conversation_id: str, user_id: int) -> bool:
        return (
            db.session.execute(
                db.select(ConversationMember.id).filter_by(
                    conversation_id=conversation_id, user_id=user_id
                )
            ).scalar_one_or_none()
            is not None
        )

    def list_for_user(self, user: User) -> list[Conversation]:
        query = (
            db.select(Conversation)
            .join(ConversationMember)
            .filter(ConversationMember.user_id == user.id)
            .order_by(Conversation.created_at.desc())
        )
        return list(db.session.execute(query).unique().scalars())

    def create(self, creator: User, user_ids: list[int]) -> Conversation:
        member_ids = list(dict.fromkeys([*user_ids, creator.id]))

        users = list(
            db.session.execute(
                db.select(User).filter(User.id.in_(member_ids))
            ).scalars()
        )
        if len(users) != len(member_ids):
            found = {user.id for user in users}
            missing = [user_id for user_id in member_ids if user_id not in found]
            raise InvalidParticipantsError(
                f"Unknown user id(s): {', '.join(map(str, missing))}"
            )

        conversation = Conversation()
        conversation.members = [
            ConversationMember(user_id=user_id) for user_id in member_ids
        ]
        db.session.add(conversation)
        db.session.commit()
        return conversation


def build_conversation_service() -> ConversationService:
    return ConversationService()
