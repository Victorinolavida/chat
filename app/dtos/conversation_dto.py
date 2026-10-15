from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

from app.dtos.user_dto import UserPublicDTO


class ConversationCreateDTO(BaseModel):
    user_ids: list[int] = Field(min_length=1)

    @field_validator("user_ids")
    @classmethod
    def unique_user_ids(cls, value: list[int]) -> list[int]:
        seen = []
        for user_id in value:
            if user_id not in seen:
                seen.append(user_id)
        if not seen:
            raise ValueError("at least one user id is required")
        return seen


class ConversationReadDTO(BaseModel):
    id: str
    created_at: datetime
    members: list[UserPublicDTO]

    @field_validator("created_at", mode="before")
    @classmethod
    def assume_utc(cls, value):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @classmethod
    def from_model(cls, conversation) -> "ConversationReadDTO":
        return cls(
            id=conversation.id,
            created_at=conversation.created_at,
            members=[
                UserPublicDTO.model_validate(member.user)
                for member in conversation.members
            ],
        )
