import pytest

from app.media import (
    CATEGORY_AUDIO,
    CATEGORY_IMAGE,
    CATEGORY_TEXT,
    UnsupportedMediaError,
    extension_of,
    human_size,
    is_previewable,
    resolve_media,
)


def test_extension_is_lowercased():
    assert extension_of("Track.MP3") == "mp3"


def test_extension_missing():
    assert extension_of("README") == ""


def test_resolve_text_format():
    media = resolve_media("notes.txt")

    assert media.extension == "txt"
    assert media.content_type == "text/plain"
    assert media.category == CATEGORY_TEXT


def test_resolve_json_format():
    media = resolve_media("data.json", "application/json")

    assert media.content_type == "application/json"
    assert media.category == CATEGORY_TEXT


def test_resolve_audio_format():
    media = resolve_media("song.mp3")

    assert media.content_type == "audio/mpeg"
    assert media.category == CATEGORY_AUDIO


def test_alias_content_type_is_normalized():
    media = resolve_media("song.mp3", "audio/mp3")

    assert media.content_type == "audio/mpeg"


def test_content_type_parameters_are_ignored():
    media = resolve_media("notes.txt", "text/plain; charset=utf-8")

    assert media.content_type == "text/plain"


def test_octet_stream_falls_back_to_canonical():
    media = resolve_media("photo.png", "application/octet-stream")

    assert media.content_type == "image/png"


def test_rejects_unknown_extension():
    with pytest.raises(UnsupportedMediaError):
        resolve_media("malware.exe")


def test_rejects_extensionless_file():
    with pytest.raises(UnsupportedMediaError):
        resolve_media("README")


def test_rejects_mismatched_content_type():
    with pytest.raises(UnsupportedMediaError):
        resolve_media("photo.png", "application/pdf")


def test_human_size_units():
    assert human_size(0) == "0 B"
    assert human_size(999) == "999 B"
    assert human_size(1024) == "1.0 KB"
    assert human_size(5 * 1024 * 1024) == "5.0 MB"
    assert human_size(None) is None


def test_is_previewable():
    assert is_previewable(CATEGORY_IMAGE)
    assert is_previewable(CATEGORY_AUDIO)
    assert not is_previewable(CATEGORY_TEXT)
    assert not is_previewable(None)
