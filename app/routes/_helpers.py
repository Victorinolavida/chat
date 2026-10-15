from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.models.user import User


def current_user() -> User | None:
    identity = get_jwt_identity()
    if identity is None:
        return None
    return db.session.get(User, int(identity))
