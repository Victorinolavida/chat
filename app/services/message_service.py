from app.extensions import db
from app.models.message import Message
from app.models.user import User


class MessageService:
    def create(
        self,
        sender: User,
        body: str,
        conversation_id: str | None = None,
    ) -> Message:
        message = Message(
            from_user_id=sender.id,
            conversation_id=conversation_id,
            body=body,
        )
        db.session.add(message)
        db.session.commit()
        return message

    def list_recent(self, limit: int = 50) -> list[Message]:
        rows = db.session.execute(
            db.select(Message).order_by(Message.created_at.desc()).limit(limit)
        ).scalars()
        return list(reversed(rows.all()))

    def list_by_conversation(
        self, conversation_id: str | None = None, limit: int = 50
    ) -> list[Message]:
        query = db.select(Message)
        if conversation_id is None:
            query = query.filter(Message.conversation_id.is_(None))
        else:
            query = query.filter(Message.conversation_id == conversation_id)
        query = query.order_by(Message.created_at.desc()).limit(limit)
        rows = db.session.execute(query).scalars()
        return list(reversed(rows.all()))


def build_message_service() -> MessageService:
    return MessageService()
