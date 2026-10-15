from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator, model_validator

from app.dtos.attachment_dto import AttachmentDownloadDTO, AttachmentReadDTO
from app.services.storage_service import build_storage_service


class MessageCreateDTO(BaseModel):
    body: str = Field(default="", max_length=2000)
    attachment_ids: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("body")
    @classmethod
    def strip_body(cls, value: str) -> str:
        return value.strip()

    @field_validator("attachment_ids")
    @classmethod
    def dedupe_attachment_ids(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def require_content(self) -> "MessageCreateDTO":
        if not self.body and not self.attachment_ids:
            raise ValueError("message must include text or at least one attachment")
        return self


def _attachment_with_url(attachment) -> AttachmentDownloadDTO:
    return AttachmentDownloadDTO(
        **AttachmentReadDTO.from_model(attachment).model_dump(),
        download_url=build_storage_service().presigned_url(attachment.object_key),
    )


class MessageReadDTO(BaseModel):
    id: str
    from_user_id: int
    from_username: str
    conversation_id: str | None = None
    body: str
    attachments: list[AttachmentDownloadDTO] = Field(default_factory=list)
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
            attachments=[
                _attachment_with_url(attachment)
                for attachment in message.attachments
            ],
            created_at=message.created_at,
        )
