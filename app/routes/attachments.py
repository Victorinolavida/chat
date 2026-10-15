from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from pydantic import ValidationError

from app.dtos.attachment_dto import (
    AttachmentCreateDTO,
    AttachmentDownloadDTO,
    AttachmentReadDTO,
    AttachmentUploadDTO,
)
from app.models.user import User
from app.responses import read_json_object, validation_error_response
from app.routes._helpers import current_user
from app.services.attachment_service import build_attachment_service
from app.services.conversation_service import build_conversation_service

attachments_bp = Blueprint("attachments", __name__, url_prefix="/attachments")


def _can_view(user: User, attachment) -> bool:
    if attachment.conversation_id is None:
        return True
    if attachment.user_id == user.id:
        return True
    return build_conversation_service().is_member(
        attachment.conversation_id, user.id
    )


@attachments_bp.post("")
@jwt_required()
def create_attachment():
    body, error = read_json_object()
    if error is not None:
        return error

    try:
        payload = AttachmentCreateDTO.model_validate(body)
    except ValidationError as validation_error:
        return validation_error_response(validation_error)

    me = current_user()
    if payload.conversation_id is not None:
        conv_service = build_conversation_service()
        if not conv_service.is_member(payload.conversation_id, me.id):
            return (
                jsonify(
                    {"error": "Forbidden", "message": "Not a member of conversation"}
                ),
                403,
            )

    attachment, upload_url = build_attachment_service().create_upload(
        uploader=me,
        filename=payload.filename,
        content_type=payload.content_type,
        size_bytes=payload.size_bytes,
        conversation_id=payload.conversation_id,
    )

    dto = AttachmentUploadDTO(
        **AttachmentReadDTO.from_model(attachment).model_dump(),
        object_key=attachment.object_key,
        upload_url=upload_url,
    )
    return jsonify(dto.model_dump(mode="json")), 201


@attachments_bp.get("")
@jwt_required()
def list_attachments():
    me = current_user()
    conversation_id = request.args.get("conversation_id") or None

    if conversation_id is not None:
        if not build_conversation_service().is_member(conversation_id, me.id):
            return jsonify(
                {"error": "Forbidden", "message": "Not a member of conversation"}
            ), 403

    attachments = build_attachment_service().list_by_conversation(conversation_id)
    return jsonify(
        {
            "conversation_id": conversation_id,
            "attachments": [
                AttachmentReadDTO.from_model(attachment).model_dump(mode="json")
                for attachment in attachments
            ],
        }
    )


@attachments_bp.get("/<attachment_id>")
@jwt_required()
def get_attachment(attachment_id: str):
    me = current_user()
    attachment = build_attachment_service().get(attachment_id)
    if attachment is None:
        return jsonify({"error": "Not found", "message": "Unknown attachment"}), 404

    if not _is_visible(me, attachment):
        return jsonify(
            {"error": "Forbidden", "message": "Not allowed to access attachment"}
        ), 403

    download_url = build_attachment_service().download_url(attachment)
    dto = AttachmentDownloadDTO(
        **AttachmentReadDTO.from_model(attachment).model_dump(),
        download_url=download_url,
    )
    return jsonify(dto.model_dump(mode="json"))


def _is_visible(user, attachment) -> bool:
    if attachment.user_id == user.id:
        return True
    if attachment.conversation_id is None:
        return True
    return build_conversation_service().is_member(
        attachment.conversation_id, user.id
    )
