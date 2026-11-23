import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    # Server
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5000"))
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-visitor-slideshow-2026")

    # Storage Paths
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "uploads"))
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "visitor.db"))
    
    # Upload Constraints
    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_SIZE_MB * 1024 * 1024  # Flask request limit
    MAX_FILES_PER_UPLOAD = int(os.getenv("MAX_FILES_PER_UPLOAD", "5"))
    ALLOWED_EXTENSIONS = set(os.getenv("ALLOWED_EXTENSIONS", "jpg,jpeg,png,webp").lower().split(","))
    MAX_IMAGE_DIMENSION = 4096  # Max width/height to prevent decompression bombs

    # Slideshow Settings
    SLIDESHOW_DISPLAY_DURATION = int(os.getenv("SLIDESHOW_DISPLAY_DURATION", "8"))
    AMBIENT_LOOP_ENABLED = os.getenv("AMBIENT_LOOP_ENABLED", "True").lower() in ("true", "1", "t")

    # Privacy & Retention
    REQUIRE_CONSENT = os.getenv("REQUIRE_CONSENT", "True").lower() in ("true", "1", "t")
    PHOTO_RETENTION_HOURS = int(os.getenv("PHOTO_RETENTION_HOURS", "24"))

    @classmethod
    def ensure_directories(cls):
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Path(cls.DATABASE_PATH).parent, exist_ok=True)
