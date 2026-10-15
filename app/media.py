from dataclasses import dataclass

MAX_UPLOAD_BYTES = 50 * 1024 * 1024

CATEGORY_TEXT = "text"
CATEGORY_IMAGE = "image"
CATEGORY_AUDIO = "audio"
CATEGORY_VIDEO = "video"
CATEGORY_DOCUMENT = "document"

# extension -> (canonical content type, preview category)
_ALLOWED_TYPES: dict[str, tuple[str, str]] = {
    "txt": ("text/plain", CATEGORY_TEXT),
    "log": ("text/plain", CATEGORY_TEXT),
    "md": ("text/markdown", CATEGORY_TEXT),
    "csv": ("text/csv", CATEGORY_TEXT),
    "json": ("application/json", CATEGORY_TEXT),
    "xml": ("application/xml", CATEGORY_TEXT),
    "yml": ("application/yaml", CATEGORY_TEXT),
    "yaml": ("application/yaml", CATEGORY_TEXT),
    "png": ("image/png", CATEGORY_IMAGE),
    "jpg": ("image/jpeg", CATEGORY_IMAGE),
    "jpeg": ("image/jpeg", CATEGORY_IMAGE),
    "gif": ("image/gif", CATEGORY_IMAGE),
    "webp": ("image/webp", CATEGORY_IMAGE),
    "svg": ("image/svg+xml", CATEGORY_IMAGE),
    "bmp": ("image/bmp", CATEGORY_IMAGE),
    "heic": ("image/heic", CATEGORY_IMAGE),
    "mp3": ("audio/mpeg", CATEGORY_AUDIO),
    "wav": ("audio/wav", CATEGORY_AUDIO),
    "ogg": ("audio/ogg", CATEGORY_AUDIO),
    "oga": ("audio/ogg", CATEGORY_AUDIO),
    "m4a": ("audio/mp4", CATEGORY_AUDIO),
    "aac": ("audio/aac", CATEGORY_AUDIO),
    "flac": ("audio/flac", CATEGORY_AUDIO),
    "mp4": ("video/mp4", CATEGORY_VIDEO),
    "webm": ("video/webm", CATEGORY_VIDEO),
    "mov": ("video/quicktime", CATEGORY_VIDEO),
    "pdf": ("application/pdf", CATEGORY_DOCUMENT),
}

_CONTENT_TYPE_ALIASES = {
    "image/jpg": "image/jpeg",
    "audio/mp3": "audio/mpeg",
    "audio/x-wav": "audio/wav",
    "audio/x-m4a": "audio/mp4",
    "application/x-yaml": "application/yaml",
    "text/x-markdown": "text/markdown",
}

_OCTET_STREAM = {"application/octet-stream", "binary/octet-stream", ""}


class UnsupportedMediaError(ValueError):
    pass


@dataclass(frozen=True)
class Media:
    extension: str
    content_type: str
    category: str


def extension_of(filename: str) -> str:
    _, separator, extension = filename.rpartition(".")
    return extension.lower() if separator else ""


def _normalize_content_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    normalized = content_type.split(";", 1)[0].strip().lower()
    if normalized in _OCTET_STREAM:
        return None
    return _CONTENT_TYPE_ALIASES.get(normalized, normalized)


def resolve_media(filename: str, content_type: str | None = None) -> Media:
    extension = extension_of(filename)
    entry = _ALLOWED_TYPES.get(extension)
    if entry is None:
        raise UnsupportedMediaError(
            f"unsupported file type {extension or ''!r}: "
            f"allowed types are {', '.join(sorted(_ALLOWED_TYPES))}"
        )

    canonical, category = entry
    normalized = _normalize_content_type(content_type)
    if normalized is not None and normalized != canonical:
        raise UnsupportedMediaError(
            f"content type {content_type!r} does not match .{extension} files"
        )

    return Media(extension=extension, content_type=canonical, category=category)


def human_size(num_bytes: int | None) -> str | None:
    if num_bytes is None:
        return None
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return None


def is_previewable(category: str | None) -> bool:
    return category in {CATEGORY_IMAGE, CATEGORY_AUDIO, CATEGORY_VIDEO}
