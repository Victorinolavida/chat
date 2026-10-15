import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"

load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{INSTANCE_DIR / 'chat.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5000"))
    DEBUG = os.getenv("DEBUG", "true").lower() in {"1", "true", "yes", "on"}

    SOCKETIO_PATH = os.getenv("SOCKETIO_PATH", "/ws")

    STORAGE_ENDPOINT = os.getenv("SILO_ENDPOINT", "http://localhost:9000")
    STORAGE_ACCESS_KEY = os.getenv("SILO_ACCESS_KEY", "admin")
    STORAGE_SECRET_KEY = os.getenv("SILO_SECRET_KEY", "adminadmin")
    STORAGE_BUCKET = os.getenv("SILO_BUCKET", "chat")
    STORAGE_REGION = os.getenv("SILO_REGION", "us-east-1")
    STORAGE_URL_TTL = int(os.getenv("SILO_URL_TTL", "3600"))
