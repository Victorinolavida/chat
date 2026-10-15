from app.extensions import db
from app.models.attachment import Attachment
from app.models.message import Message
from app.models.user import User


class InvalidAttachmentError(Exception):
    pass


class MessageService:
    def create(
        self,
        sender: User,
        body: str,
        conversation_id: str | None = None,
        attachment_ids: list[str] | None = None,
    ) -> Message:
        message = Message(
            from_user_id=sender.id,
            conversation_id=conversation_id,
            body=body,
        )
        try:
            db.session.add(message)
            db.session.flush()
            if attachment_ids:
                self._link_attachments(sender, message, attachment_ids)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return message

    @staticmethod
    def _link_attachments(
        sender: User, message: Message, attachment_ids: list[str]
    ) -> None:
        attachments = list(
            db.session.execute(
                db.select(Attachment).filter(Attachment.id.in_(attachment_ids))
            ).scalars()
        )
        found = {attachment.id: attachment for attachment in attachments}
        missing = [attachment_id for attachment_id in attachment_ids if attachment_id not in found]
        if missing:
            raise InvalidAttachmentError(
                f"unknown attachment(s): {', '.join(missing)}"
            )

        for attachment in attachments:
            if attachment.user_id != sender.id:
                raise InvalidAttachmentError(
                    "attachment belongs to another user"
                )
            if attachment.message_id is not None:
                raise InvalidAttachmentError("attachment is already attached")
            if attachment.conversation_id != message.conversation_id:
                raise InvalidAttachmentError(
                    "attachment does not belong to this conversation"
                )
            attachment.message_id = message.id

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
