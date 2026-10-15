from datetime import datetime, timezone

from app.extensions import db
from app.models.base import uuid7_str


class Attachment(db.Model):
    __tablename__ = "attachments"

    id = db.Column(db.String(36), primary_key=True, default=uuid7_str)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    conversation_id = db.Column(
        db.String(36), db.ForeignKey("conversations.id"), nullable=True, index=True
    )
    object_key = db.Column(db.String(512), nullable=False, unique=True)
    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(255), nullable=True)
    extension = db.Column(db.String(16), nullable=True, index=True)
    category = db.Column(db.String(32), nullable=True, index=True)
    size_bytes = db.Column(db.BigInteger, nullable=True)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    user = db.relationship("User", backref="attachments")

    def __repr__(self) -> str:
        return f"<Attachment {self.id} key={self.object_key}>"
