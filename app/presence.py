import threading

_lock = threading.Lock()
_connections: dict[str, int] = {}


def add(sid: str, user_id: int) -> None:
    with _lock:
        _connections[sid] = user_id


def remove(sid: str) -> int | None:
    with _lock:
        return _connections.pop(sid, None)


def online_user_ids() -> set[int]:
    with _lock:
        return set(_connections.values())


def is_online(user_id: int) -> bool:
    with _lock:
        return user_id in _connections.values()


def reset() -> None:
    with _lock:
        _connections.clear()
