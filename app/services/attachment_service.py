from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.attachment import Attachment
from app.models.base import uuid7_str
from app.models.user import User
from app.services.storage_service import build_storage_service


class AttachmentService:
    @staticmethod
    def _object_key(
        attachment_id: str, conversation_id: str | None, filename: str
    ) -> str:
        prefix = f"conversations/{conversation_id}" if conversation_id else "general"
        return f"{prefix}/attachments/{attachment_id}/{filename}"

    def create_upload(
        self,
        uploader: User,
        filename: str,
        content_type: str | None = None,
        size_bytes: int | None = None,
        conversation_id: str | None = None,
    ) -> tuple[Attachment, str]:
        attachment_id = uuid7_str()
        safe_name = secure_filename(filename) or "file"
        object_key = self._object_key(attachment_id, conversation_id, safe_name)

        attachment = Attachment(
            id=attachment_id,
            user_id=uploader.id,
            conversation_id=conversation_id,
            object_key=object_key,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
        )
        db.session.add(attachment)
        db.session.commit()

        upload_url = build_storage_service().presigned_upload(object_key, content_type)
        return attachment, upload_url

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


def build_attachment_service() -> AttachmentService:
    return AttachmentService()
