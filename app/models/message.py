import uuid
from datetime import datetime, timezone

from app.extensions import db


def uuid7_str() -> str:
    return str(uuid.uuid7())


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.String(36), primary_key=True, default=uuid7_str)
    from_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    to_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
    )
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    from_user = db.relationship(
        "User", foreign_keys=[from_user_id], backref="sent_messages"
    )
    to_user = db.relationship(
        "User", foreign_keys=[to_user_id], backref="received_messages"
    )

    def __repr__(self) -> str:
        return f"<Message {self.id} from={self.from_user_id}>"
