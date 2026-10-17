"""Diagnose Cloudinary credentials from .env.txt"""
import cloudinary, cloudinary.uploader, io, traceback
import requests as req
from app.core.config import settings

print("CLOUD_NAME :", settings.CLOUDINARY_CLOUD_NAME)
print("API_KEY    :", settings.CLOUDINARY_API_KEY[:6], "...")
print("API_SECRET :", settings.CLOUDINARY_API_SECRET[:4], "...", settings.CLOUDINARY_API_SECRET[-4:], f"(len={len(settings.CLOUDINARY_API_SECRET)})")

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)

img = req.get("https://picsum.photos/100/100.jpg", timeout=10).content
print(f"Image size: {len(img)} bytes")

try:
    result = cloudinary.uploader.upload(
        io.BytesIO(img), folder="civicfix/test", resource_type="image", timeout=20
    )
    print("SUCCESS:", result["secure_url"])
except Exception as e:
    print("FULL ERROR:")
    traceback.print_exc()
