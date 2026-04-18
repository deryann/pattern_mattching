from __future__ import annotations

import base64
import binascii
from io import BytesIO

import cv2
import numpy as np

MAX_IMAGE_BYTES = 20 * 1024 * 1024

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"


class ImageDecodeError(ValueError):
    pass


class ImageTooLargeError(ValueError):
    pass


def _strip_data_url_prefix(s: str) -> str:
    if s.startswith("data:"):
        comma = s.find(",")
        if comma != -1:
            return s[comma + 1 :]
    return s


def validate_image_bytes(buf: bytes) -> None:
    if len(buf) == 0:
        raise ImageDecodeError("empty image")
    if len(buf) > MAX_IMAGE_BYTES:
        raise ImageTooLargeError(f"image exceeds {MAX_IMAGE_BYTES} bytes")
    if not (buf.startswith(_PNG_MAGIC) or buf.startswith(_JPEG_MAGIC)):
        raise ImageDecodeError("only PNG and JPEG are supported")


def decode_base64(data: str) -> np.ndarray:
    """Decode a base64 string (optional data URL prefix) into a BGR ndarray."""
    cleaned = _strip_data_url_prefix(data).strip()
    try:
        raw = base64.b64decode(cleaned, validate=True)
    except binascii.Error as exc:
        raise ImageDecodeError(f"invalid base64: {exc}") from exc
    validate_image_bytes(raw)
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ImageDecodeError("cv2 failed to decode image")
    return img


def encode_png_base64(img: np.ndarray) -> str:
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise ImageDecodeError("cv2 failed to encode PNG")
    return base64.b64encode(buf.tobytes()).decode("ascii")
