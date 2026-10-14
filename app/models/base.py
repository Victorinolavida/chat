import uuid
from datetime import datetime, timezone


def uuid7_str() -> str:
    return str(uuid.uuid7())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
