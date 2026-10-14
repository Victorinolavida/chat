from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


class MessageCreateDTO(BaseModel):
    body: str = Field(min_length=1, max_length=2000)

    @field_validator("body")
    @classmethod
    def strip_and_require_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message must not be empty")
        return stripped


class MessageReadDTO(BaseModel):
    id: str
    from_user_id: int
    from_username: str
    conversation_id: str | None = None
    body: str
    created_at: datetime

    @field_validator("created_at", mode="before")
    @classmethod
    def assume_utc(cls, value):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @classmethod
    def from_model(cls, message) -> "MessageReadDTO":
        return cls(
            id=message.id,
            from_user_id=message.from_user_id,
            from_username=message.from_user.username,
            conversation_id=message.conversation_id,
            body=message.body,
            created_at=message.created_at,
        )
