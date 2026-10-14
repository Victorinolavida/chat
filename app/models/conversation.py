from datetime import datetime, timezone

from app.extensions import db
from app.models.base import uuid7_str


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.String(36), primary_key=True, default=uuid7_str)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    members = db.relationship(
        "ConversationMember",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def member_ids(self) -> list[int]:
        return [member.user_id for member in self.members]

    def __repr__(self) -> str:
        return f"<Conversation {self.id}>"


class ConversationMember(db.Model):
    __tablename__ = "conversation_members"
    __table_args__ = (
        db.UniqueConstraint(
            "conversation_id", "user_id", name="uq_conversation_member"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.String(36), db.ForeignKey("conversations.id"), nullable=False, index=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    conversation = db.relationship("Conversation", back_populates="members")
    user = db.relationship("User", lazy="joined")

    def __repr__(self) -> str:
        return f"<ConversationMember conv={self.conversation_id} user={self.user_id}>"
