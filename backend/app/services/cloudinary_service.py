"""
Cloudinary upload service.

Validates each file BEFORE uploading:
  - content_type must be image/jpeg, image/png, or image/webp
  - file size must be <= MAX_BYTES (5 MB)

Raises HTTPException(400) for validation errors.
Raises HTTPException(502) if Cloudinary upload fails or times out.
Never returns a placeholder — callers must handle 502 and abort the transaction.
"""
from __future__ import annotations

import io

import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile

from app.core.config import settings

# ── Constants ─────────────────────────────────────────────────────────────────

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
UPLOAD_TIMEOUT = 30           # seconds

# Configure once at import time (idempotent — cloudinary.config is re-entrant)
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)


# ── Public API ────────────────────────────────────────────────────────────────

async def validate_and_upload(file: UploadFile, folder: str = "civicfix/issues") -> str:
    """
    Read, validate, and upload a single UploadFile to Cloudinary.

    Returns the secure_url string.
    Raises HTTPException(400) for invalid files, HTTPException(502) on upload error.
    """
    # --- content-type check ---
    ct = (file.content_type or "").lower()
    if ct not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"'{file.filename}': unsupported file type '{ct}'. "
                   f"Only JPEG, PNG, and WebP images are accepted.",
        )

    # --- read into memory so we can check size AND send to Cloudinary ---
    data = await file.read()
    if len(data) > MAX_BYTES:
        mb = len(data) / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"'{file.filename}': file is {mb:.1f} MB — maximum allowed size is 5 MB.",
        )

    # --- upload ---
    try:
        result = cloudinary.uploader.upload(
            io.BytesIO(data),
            folder=folder,
            resource_type="image",
            timeout=UPLOAD_TIMEOUT,
        )
        return result["secure_url"]
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Photo upload failed: could not reach Cloudinary. "
                   f"Please try again in a moment. ({type(exc).__name__})",
        ) from exc


async def upload_many(
    files: list[UploadFile],
    *,
    min_count: int = 0,
    max_count: int = 3,
    folder: str = "civicfix/issues",
) -> list[str]:
    """
    Validate and upload 0–max_count photos.
    Returns list of secure_urls in order.
    Raises HTTPException(400) if count is out of range or any file is invalid.
    Raises HTTPException(502) if any upload fails.
    """
    if len(files) < min_count:
        raise HTTPException(
            status_code=400,
            detail=f"At least {min_count} photo(s) required.",
        )
    if len(files) > max_count:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {max_count} photo(s) allowed per issue.",
        )

    urls: list[str] = []
    for f in files:
        url = await validate_and_upload(f, folder=folder)
        urls.append(url)
    return urls
