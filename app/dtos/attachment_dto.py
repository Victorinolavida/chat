from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


class AttachmentCreateDTO(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str | None = Field(default=None, max_length=255)
    size_bytes: int | None = Field(default=None, ge=0)
    conversation_id: str | None = None

    @field_validator("filename")
    @classmethod
    def strip_and_require_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("filename must not be empty")
        return stripped


class AttachmentReadDTO(BaseModel):
    id: str
    user_id: int
    conversation_id: str | None = None
    filename: str
    content_type: str | None = None
    size_bytes: int | None = None
    created_at: datetime

    @field_validator("created_at", mode="before")
    @classmethod
    def assume_utc(cls, value):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @classmethod
    def from_model(cls, attachment) -> "AttachmentReadDTO":
        return cls(
            id=attachment.id,
            user_id=attachment.user_id,
            conversation_id=attachment.conversation_id,
            filename=attachment.filename,
            content_type=attachment.content_type,
            size_bytes=attachment.size_bytes,
            created_at=attachment.created_at,
        )


class AttachmentUploadDTO(AttachmentReadDTO):
    object_key: str
    upload_url: str


class AttachmentDownloadDTO(AttachmentReadDTO):
    download_url: str
