from flask import Blueprint, render_template, current_app, request
from app.config import Config
from app.services.visitor_service import VisitorService

views_bp = Blueprint("views", __name__)

@views_bp.route("/")
def upload_kiosk():
    """Visitor self-service check-in & photo upload portal."""
    return render_template(
        "upload.html",
        max_size_mb=Config.MAX_UPLOAD_SIZE_MB,
        max_files=Config.MAX_FILES_PER_UPLOAD,
        allowed_extensions=sorted(list(Config.ALLOWED_EXTENSIONS))
    )

@views_bp.route("/display")
def tv_slideshow():
    """Smart TV / Large display slideshow screen with live SSE listener and QR code."""
    upload_url = request.host_url.rstrip("/")
    return render_template(
        "slideshow.html",
        duration=Config.SLIDESHOW_DISPLAY_DURATION,
        upload_url=upload_url
    )

@views_bp.route("/gallery")
def visitor_gallery():
    """Visitor photo browser & self-service privacy deletion portal."""
    photos = VisitorService.get_all_approved_photos(
        db_path=current_app.config["DATABASE_PATH"]
    )
    return render_template("gallery.html", photos=[p.to_dict() for p in photos])
