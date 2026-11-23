import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import RequestEntityTooLarge
from app.config import Config
from app.services.visitor_service import VisitorService
from app.services.image_service import ImageService, ImageValidationError
from app.services.slideshow_queue import slideshow_manager

api_bp = Blueprint("api", __name__)

@api_bp.route("/upload", methods=["POST"])
def upload_photos():
    """
    Handle visitor photo upload:
    1. Parse and validate form fields (name, secondary_identifier, consent).
    2. Identify or register visitor (detecting if returning).
    3. Validate and process each photo file (Pillow verify, EXIF sanitize, UUID).
    4. Save to database.
    5. If consent given, enqueue to TV slideshow priority queue with past photos.
    """
    name = (request.form.get("name") or "").strip()
    secondary_identifier = (request.form.get("secondary_identifier") or "").strip()
    consent_raw = request.form.get("consent", "true").lower()
    consent = consent_raw in ("true", "1", "yes", "on")

    # Validation
    if not name:
        return jsonify({"error": "Visitor name is required."}), 400
    if len(name) > 100:
        return jsonify({"error": "Name is too long (maximum 100 characters)."}), 400

    if not secondary_identifier:
        return jsonify({
            "error": "Secondary identifier (phone, email, or handle) is required to identify returning visitors."
        }), 400
    if len(secondary_identifier) > 120:
        return jsonify({"error": "Secondary identifier is too long."}), 400

    files = request.files.getlist("photos")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "At least one photo must be selected."}), 400

    if len(files) > Config.MAX_FILES_PER_UPLOAD:
        return jsonify({
            "error": f"Too many files selected. Maximum is {Config.MAX_FILES_PER_UPLOAD} photos per upload."
        }), 400

    try:
        # 1. Resolve visitor identity
        visitor, is_returning = VisitorService.get_or_create_visitor(
            name=name,
            secondary_identifier=secondary_identifier,
            db_path=current_app.config["DATABASE_PATH"]
        )

        saved_photos = []
        new_photo_ids = []

        # 2. Process and validate each file
        for file in files:
            if not file or not file.filename:
                continue

            # Process with multi-layer image validation pipeline
            image_meta = ImageService.process_and_save_image(file)

            # Insert into database
            photo = VisitorService.save_photo_record(
                visitor_id=visitor.id,
                image_meta=image_meta,
                consent_display=consent,
                visit_number=visitor.visit_count,
                db_path=current_app.config["DATABASE_PATH"]
            )
            saved_photos.append(photo.to_dict())
            new_photo_ids.append(photo.id)

        # 3. Retrieve past photos if visitor is returning and consent given
        past_photos_dicts = []
        if consent:
            if is_returning:
                past_photos = VisitorService.get_past_photos_for_visitor(
                    visitor_id=visitor.id,
                    exclude_photo_ids=new_photo_ids,
                    db_path=current_app.config["DATABASE_PATH"]
                )
                past_photos_dicts = [p.to_dict() for p in past_photos]

            # 4. Enqueue into live slideshow priority queue & broadcast to TV displays
            slideshow_manager.enqueue_live_upload(
                visitor_name=visitor.name,
                is_returning=is_returning,
                visit_count=visitor.visit_count,
                new_photos=saved_photos,
                past_photos=past_photos_dicts,
                duration=Config.SLIDESHOW_DISPLAY_DURATION
            )

        message = (
            f"Welcome back, {visitor.name}! Your new photo{'s' if len(saved_photos) > 1 else ''} and "
            f"{len(past_photos_dicts)} past photos are playing on the slideshow display."
            if is_returning and consent
            else f"Thank you, {visitor.name}! Your photo{'s have' if len(saved_photos) > 1 else ' has'} been added to the slideshow display."
            if consent
            else f"Thank you, {visitor.name}! Your photos were saved securely (not displayed on public screens as per your privacy preference)."
        )

        return jsonify({
            "success": True,
            "message": message,
            "is_returning": is_returning,
            "visit_count": visitor.visit_count,
            "visitor": visitor.to_dict(),
            "pin": visitor.pin,
            "new_photos": saved_photos,
            "past_photos": past_photos_dicts,
            "consent_display": consent
        }), 201

    except ImageValidationError as e:
        return jsonify({"error": str(e)}), 400
    except RequestEntityTooLarge:
        return jsonify({
            "error": f"Upload rejected: total payload exceeds {Config.MAX_UPLOAD_SIZE_MB}MB limit."
        }), 413
    except Exception as e:
        current_app.logger.error(f"Upload error: {str(e)}", exc_info=True)
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@api_bp.route("/slideshow/all", methods=["GET"])
def get_slideshow_photos():
    """Retrieve all approved photos for ambient TV slideshow looping."""
    photos = VisitorService.get_all_approved_photos(
        db_path=current_app.config["DATABASE_PATH"]
    )
    return jsonify({
        "photos": [p.to_dict() for p in photos],
        "duration": Config.SLIDESHOW_DISPLAY_DURATION,
        "count": len(photos)
    })

@api_bp.route("/slideshow/status", methods=["GET"])
def get_slideshow_status():
    """Status endpoint for monitor displays."""
    status = slideshow_manager.get_queue_status()
    return jsonify(status)

@api_bp.route("/photos/delete", methods=["POST"])
def delete_photo():
    """
    Allow visitor self-service deletion:
    Visitor supplies photo_id and their personal 6-character recovery PIN.
    """
    data = request.get_json() or {}
    photo_id = data.get("photo_id")
    pin = data.get("pin")

    if not photo_id or not pin:
        return jsonify({"error": "photo_id and recovery pin are required."}), 400

    try:
        photo_id = int(photo_id)
    except ValueError:
        return jsonify({"error": "Invalid photo_id."}), 400

    deleted = VisitorService.verify_pin_and_delete_photo(
        photo_id=photo_id,
        pin=pin,
        db_path=current_app.config["DATABASE_PATH"]
    )

    if not deleted:
        return jsonify({
            "error": "Deletion failed: Photo not found or invalid recovery PIN."
        }), 403

    # Broadcast deletion event so TV display immediately drops it from memory
    slideshow_manager.broadcast_event("photo_deleted", {"photo_id": photo_id})

    return jsonify({
        "success": True,
        "message": "Photo has been removed from the slideshow and archived."
    })
