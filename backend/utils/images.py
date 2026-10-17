"""Bounded image decoding. Only raster formats are served back to browsers."""
import base64
import io
import warnings
from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 5 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 10_000_000


def validate_image(data: bytes) -> str:
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Image must be between 1 byte and 5 MiB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise HTTPException(415, "Use a JPEG, PNG or WebP image")
                content_type = Image.MIME[image.format]
                image.verify()
        return content_type
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(415, "Invalid or oversized image")


async def read_limited(upload, limit: int) -> bytes:
    data = await upload.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, "Uploaded file is too large")
    return data


async def encode_upload_to_base64(upload_file) -> tuple[str, str]:
    data = await read_limited(upload_file, MAX_IMAGE_BYTES)
    return base64.b64encode(data).decode("ascii"), validate_image(data)


def to_data_url(image_data: str, content_type: str) -> str:
    return f"data:{content_type};base64,{image_data}"


def resolve_image_field(document: dict) -> None:
    image = document.get("image", "")
    has_url = isinstance(image, str) and image.startswith(("https://", "http://"))
    if not has_url:
        document["image"] = f"/products/{document['id']}/image" if document.get("image_data") else ""
    document.pop("image_data", None)
    document.pop("image_content_type", None)
