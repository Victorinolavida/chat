from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator, model_validator

from app.media import MAX_UPLOAD_BYTES, human_size, resolve_media


class AttachmentCreateDTO(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str | None = Field(default=None, max_length=255)
    size_bytes: int = Field(gt=0, le=MAX_UPLOAD_BYTES)
    conversation_id: str | None = None

    @field_validator("filename")
    @classmethod
    def strip_filename(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("filename must not be empty")
        return stripped

    @model_validator(mode="after")
    def validate_media(self) -> "AttachmentCreateDTO":
        resolve_media(self.filename, self.content_type)
        return self


class AttachmentReadDTO(BaseModel):
    id: str
    user_id: int
    conversation_id: str | None = None
    message_id: str | None = None
    filename: str
    content_type: str | None = None
    extension: str | None = None
    category: str | None = None
    size_bytes: int | None = None
    human_size: str | None = None
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
            message_id=attachment.message_id,
            filename=attachment.filename,
            content_type=attachment.content_type,
            extension=attachment.extension,
            category=attachment.category,
            size_bytes=attachment.size_bytes,
            human_size=human_size(attachment.size_bytes),
            created_at=attachment.created_at,
        )


class AttachmentUploadDTO(AttachmentReadDTO):
    object_key: str
    upload_url: str
    upload_fields: dict[str, str]
    max_size_bytes: int = MAX_UPLOAD_BYTES


class AttachmentDownloadDTO(AttachmentReadDTO):
    download_url: str
