from app.extensions import db
from app.models.message import Message
from app.models.user import User


class MessageService:
    def create(self, sender: User, body: str, to_user: User | None = None) -> Message:
        message = Message(
            from_user_id=sender.id,
            to_user_id=to_user.id if to_user else None,
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


def build_message_service() -> MessageService:
    return MessageService()
