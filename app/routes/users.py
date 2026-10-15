from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from app import presence
from app.dtos.user_dto import UserPublicDTO
from app.extensions import db
from app.models.user import User
from app.routes._helpers import current_user

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.get("/online")
@jwt_required()
def list_online_users():
    me = current_user()
    online_ids = presence.online_user_ids() - ({me.id} if me else set())
    if not online_ids:
        return jsonify({"users": []})

    users = (
        db.session.execute(
            db.select(User)
            .filter(User.id.in_(online_ids))
            .order_by(User.username.asc())
        )
        .scalars()
        .all()
    )
    return jsonify(
        {
            "users": [
                UserPublicDTO.model_validate(user).model_dump(mode="json")
                for user in users
            ]
        }
    )
