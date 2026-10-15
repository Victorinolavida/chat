from flask import current_app
from werkzeug.utils import secure_filename

from app.extensions import db
from app.media import MAX_UPLOAD_BYTES, resolve_media
from app.models.attachment import Attachment
from app.models.base import uuid7_str
from app.models.user import User
from app.services.storage_service import StorageError, build_storage_service


class AttachmentService:
    @staticmethod
    def _object_key(
        attachment_id: str, conversation_id: str | None, filename: str
    ) -> str:
        prefix = (
            f"conversations/{conversation_id}" if conversation_id else "general_conversation"
        )
        return f"{prefix}/attachments/{attachment_id}/{filename}"

    def create_upload(
        self,
        uploader: User,
        filename: str,
        size_bytes: int,
        content_type: str | None = None,
        conversation_id: str | None = None,
    ) -> tuple[Attachment, dict]:
        media = resolve_media(filename, content_type)
        attachment_id = uuid7_str()
        stem = secure_filename(filename).rpartition(".")[0] or "file"
        safe_name = f"{stem}.{media.extension}"
        object_key = self._object_key(attachment_id, conversation_id, safe_name)

        attachment = Attachment(
            id=attachment_id,
            user_id=uploader.id,
            conversation_id=conversation_id,
            object_key=object_key,
            filename=filename,
            content_type=media.content_type,
            extension=media.extension,
            category=media.category,
            size_bytes=size_bytes,
        )
        db.session.add(attachment)
        db.session.commit()

        upload = build_storage_service().presigned_upload(
            object_key, media.content_type, max_bytes=MAX_UPLOAD_BYTES
        )
        return attachment, upload

    def get(self, attachment_id: str) -> Attachment | None:
        return db.session.get(Attachment, attachment_id)

    def list_by_conversation(
        self, conversation_id: str | None = None, limit: int = 50
    ) -> list[Attachment]:
        query = db.select(Attachment)
        if conversation_id is None:
            query = query.filter(Attachment.conversation_id.is_(None))
        else:
            query = query.filter(Attachment.conversation_id == conversation_id)
        query = query.order_by(Attachment.created_at.desc()).limit(limit)
        return list(db.session.execute(query).scalars())

    def download_url(self, attachment: Attachment) -> str:
        return build_storage_service().presigned_url(attachment.object_key)

    def delete(self, attachment: Attachment) -> None:
        build_storage_service().delete(attachment.object_key)
        db.session.delete(attachment)
        db.session.commit()

    def delete_for_message(self, message_id: str) -> int:
        attachments = list(
            db.session.execute(
                db.select(Attachment).filter(Attachment.message_id == message_id)
            ).scalars()
        )
        storage = build_storage_service()
        for attachment in attachments:
            try:
                storage.delete(attachment.object_key)
            except StorageError:
                current_app.logger.exception(
                    "failed to delete object %s from storage", attachment.object_key
                )
            db.session.delete(attachment)
        db.session.commit()
        return len(attachments)


def build_attachment_service() -> AttachmentService:
    return AttachmentService()
