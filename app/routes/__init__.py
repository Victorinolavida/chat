from app.routes.attachments import attachments_bp
from app.routes.auth import auth_bp
from app.routes.conversations import conversations_bp
from app.routes.messages import messages_bp
from app.routes.users import users_bp

__all__ = [
    "attachments_bp",
    "auth_bp",
    "conversations_bp",
    "messages_bp",
    "users_bp",
]
