import os
import io
import uuid
import secrets
from pathlib import Path
from PIL import Image, ImageOps
from werkzeug.utils import secure_filename
from app.config import Config

# Magic byte signatures for image formats
MAGIC_BYTES = {
    b"\xFF\xD8\xFF": "jpeg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"RIFF": "webp",  # RIFF....WEBP checked dynamically
}

class ImageValidationError(Exception):
    """Custom exception raised when an uploaded image fails validation."""
    pass

class ImageService:
    @staticmethod
    def validate_file_extension(filename: str) -> str:
        """Check if file extension is allowed and return normalized extension."""
        if not filename or "." not in filename:
            raise ImageValidationError("File has no extension or invalid name.")
        
        ext = filename.rsplit(".", 1)[1].lower()
        if ext not in Config.ALLOWED_EXTENSIONS:
            allowed = ", ".join(Config.ALLOWED_EXTENSIONS)
            raise ImageValidationError(f"Invalid file extension '.{ext}'. Allowed types: {allowed}")
        return ext

    @staticmethod
    def inspect_magic_bytes(file_stream) -> str:
        """Inspect file header magic bytes to prevent file extension spoofing."""
        header = file_stream.read(12)
        file_stream.seek(0)  # Rewind

        if not header:
            raise ImageValidationError("Uploaded file is empty.")

        # JPEG check
        if header.startswith(b"\xFF\xD8\xFF"):
            return "jpeg"
        # PNG check
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        # WebP check (RIFF header + WEBP tag at offset 8)
        if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
            return "webp"

        raise ImageValidationError("File content does not match recognized image signatures (JPEG, PNG, WebP).")

    @classmethod
    def process_and_save_image(cls, file_storage) -> dict:
        """
        Comprehensive image validation and sanitization pipeline:
        1. Validates extension and file size.
        2. Inspects magic bytes header.
        3. Decodes and verifies image integrity with Pillow.
        4. Transposes image based on EXIF orientation (so mobile photos aren't rotated).
        5. Strips all EXIF metadata (GPS, camera serials, personal tags) for privacy.
        6. Limits max dimensions to avoid decompression memory attacks.
        7. Saves sanitized file with a safe UUIDv4 filename.
        """
        original_filename = secure_filename(file_storage.filename or "unknown.jpg")
        ext = cls.validate_file_extension(original_filename)

        # Read into memory/buffer to verify size and inspect
        file_storage.seek(0, os.SEEK_END)
        file_size = file_storage.tell()
        file_storage.seek(0)

        if file_size == 0:
            raise ImageValidationError("Uploaded file is empty.")
        if file_size > Config.MAX_CONTENT_LENGTH:
            raise ImageValidationError(
                f"File size exceeds maximum limit of {Config.MAX_UPLOAD_SIZE_MB}MB."
            )

        # Inspect magic bytes
        cls.inspect_magic_bytes(file_storage)

        try:
            # Open with Pillow and verify structural integrity
            img = Image.open(file_storage)
            img.verify()
        except Exception as e:
            raise ImageValidationError(f"Image integrity verification failed: corrupted or invalid image file ({str(e)}).")

        # Re-open after verify() (verify() leaves image in an unusable state by design)
        file_storage.seek(0)
        img = Image.open(file_storage)

        # Check dimensions
        width, height = img.size
        if width > Config.MAX_IMAGE_DIMENSION or height > Config.MAX_IMAGE_DIMENSION:
            # Resize preserving aspect ratio
            img.thumbnail((Config.MAX_IMAGE_DIMENSION, Config.MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
            width, height = img.size

        # Auto-rotate according to EXIF orientation tag, then strip EXIF
        try:
            img = ImageOps.exif_transpose(img)
            width, height = img.size
        except Exception:
            # Ignore transposition errors on images without EXIF
            pass

        # Convert palette/RGBA to RGB if saving as JPEG
        save_format = "JPEG" if ext in ("jpg", "jpeg") else ("PNG" if ext == "png" else "WEBP")
        if save_format == "JPEG" and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Generate collision-free secure filename
        unique_name = f"{uuid.uuid4().hex}.{ext if ext != 'jpeg' else 'jpg'}"
        dest_path = os.path.join(Config.UPLOAD_FOLDER, unique_name)

        # Save sanitized image without original EXIF
        # This completely strips GPS, camera identifiers, and timestamp metadata for privacy
        img.save(dest_path, format=save_format, quality=90, optimize=True)

        return {
            "filename": unique_name,
            "original_filename": original_filename,
            "file_size": file_size,
            "mime_type": f"image/{ext if ext != 'jpg' else 'jpeg'}",
            "width": width,
            "height": height
        }
