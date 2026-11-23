import secrets
from typing import Optional, Tuple, List, Dict
from app.database import db_session
from app.models import Visitor, Photo

class VisitorService:
    @staticmethod
    def normalize_string(val: str) -> str:
        """Strip whitespace and lowercase string for consistent lookup."""
        return (val or "").strip().lower()

    @classmethod
    def get_or_create_visitor(
        cls, name: str, secondary_identifier: str, db_path=None
    ) -> Tuple[Visitor, bool]:
        """
        Identify returning visitor using compound key: (name, secondary_identifier).
        - If matching record exists:
            Increments visit_count and updates last_visit_at.
            Returns (visitor, is_returning=True).
        - If no match exists:
            Generates a unique 6-character recovery PIN.
            Creates new visitor record with visit_count=1.
            Returns (visitor, is_returning=False).
        """
        clean_name = (name or "").strip()
        clean_id = cls.normalize_string(secondary_identifier)

        if not clean_name:
            raise ValueError("Visitor name cannot be empty.")
        if not clean_id:
            raise ValueError("Visitor secondary identifier (phone or email) cannot be empty.")

        with db_session(db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, name, secondary_identifier, pin, visit_count, created_at, last_visit_at
                FROM visitors
                WHERE LOWER(name) = LOWER(?) AND secondary_identifier = ?
                """,
                (clean_name, clean_id),
            )
            row = cur.fetchone()

            if row:
                # Existing returning visitor
                visitor_id = row["id"]
                new_visit_count = row["visit_count"] + 1
                cur.execute(
                    """
                    UPDATE visitors
                    SET visit_count = ?, last_visit_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (new_visit_count, visitor_id),
                )
                cur.execute(
                    """
                    SELECT id, name, secondary_identifier, pin, visit_count, created_at, last_visit_at
                    FROM visitors WHERE id = ?
                    """,
                    (visitor_id,),
                )
                updated_row = cur.fetchone()
                visitor = Visitor(
                    id=updated_row["id"],
                    name=updated_row["name"],
                    secondary_identifier=updated_row["secondary_identifier"],
                    pin=updated_row["pin"],
                    visit_count=updated_row["visit_count"],
                    created_at=str(updated_row["created_at"]),
                    last_visit_at=str(updated_row["last_visit_at"]),
                )
                return visitor, True
            else:
                # First time visitor - generate 6-character deletion PIN
                pin = secrets.token_hex(3).upper()
                cur.execute(
                    """
                    INSERT INTO visitors (name, secondary_identifier, pin, visit_count)
                    VALUES (?, ?, ?, 1)
                    """,
                    (clean_name, clean_id, pin),
                )
                visitor_id = cur.lastrowid
                cur.execute(
                    """
                    SELECT id, name, secondary_identifier, pin, visit_count, created_at, last_visit_at
                    FROM visitors WHERE id = ?
                    """,
                    (visitor_id,),
                )
                new_row = cur.fetchone()
                visitor = Visitor(
                    id=new_row["id"],
                    name=new_row["name"],
                    secondary_identifier=new_row["secondary_identifier"],
                    pin=new_row["pin"],
                    visit_count=1,
                    created_at=str(new_row["created_at"]),
                    last_visit_at=str(new_row["last_visit_at"]),
                )
                return visitor, False

    @classmethod
    def save_photo_record(
        cls,
        visitor_id: int,
        image_meta: dict,
        consent_display: bool,
        visit_number: int,
        db_path=None,
    ) -> Photo:
        """Insert photo record into database linked to visitor."""
        with db_session(db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO photos (
                    visitor_id, filename, original_filename, file_size,
                    mime_type, width, height, consent_display, is_deleted, visit_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    visitor_id,
                    image_meta["filename"],
                    image_meta["original_filename"],
                    image_meta["file_size"],
                    image_meta["mime_type"],
                    image_meta.get("width"),
                    image_meta.get("height"),
                    1 if consent_display else 0,
                    visit_number,
                ),
            )
            photo_id = cur.lastrowid
            cur.execute(
                """
                SELECT p.*, v.name as visitor_name
                FROM photos p
                JOIN visitors v ON p.visitor_id = v.id
                WHERE p.id = ?
                """,
                (photo_id,),
            )
            row = cur.fetchone()
            return Photo(
                id=row["id"],
                visitor_id=row["visitor_id"],
                filename=row["filename"],
                original_filename=row["original_filename"],
                file_size=row["file_size"],
                mime_type=row["mime_type"],
                width=row["width"],
                height=row["height"],
                consent_display=bool(row["consent_display"]),
                is_deleted=bool(row["is_deleted"]),
                visit_number=row["visit_number"],
                uploaded_at=str(row["uploaded_at"]),
                visitor_name=row["visitor_name"],
            )

    @classmethod
    def get_past_photos_for_visitor(
        cls, visitor_id: int, exclude_photo_ids: List[int] = None, db_path=None
    ) -> List[Photo]:
        """Fetch previously uploaded photos by visitor that have public display consent."""
        exclude_photo_ids = exclude_photo_ids or []
        with db_session(db_path) as conn:
            cur = conn.cursor()
            query = """
                SELECT p.*, v.name as visitor_name
                FROM photos p
                JOIN visitors v ON p.visitor_id = v.id
                WHERE p.visitor_id = ? 
                  AND p.consent_display = 1 
                  AND p.is_deleted = 0
            """
            params = [visitor_id]
            if exclude_photo_ids:
                placeholders = ",".join("?" for _ in exclude_photo_ids)
                query += f" AND p.id NOT IN ({placeholders})"
                params.extend(exclude_photo_ids)
            query += " ORDER BY p.uploaded_at ASC"

            cur.execute(query, params)
            rows = cur.fetchall()
            return [
                Photo(
                    id=r["id"],
                    visitor_id=r["visitor_id"],
                    filename=r["filename"],
                    original_filename=r["original_filename"],
                    file_size=r["file_size"],
                    mime_type=r["mime_type"],
                    width=r["width"],
                    height=r["height"],
                    consent_display=bool(r["consent_display"]),
                    is_deleted=bool(r["is_deleted"]),
                    visit_number=r["visit_number"],
                    uploaded_at=str(r["uploaded_at"]),
                    visitor_name=r["visitor_name"],
                )
                for r in rows
            ]

    @classmethod
    def get_all_approved_photos(cls, db_path=None) -> List[Photo]:
        """Fetch all non-deleted photos with public display consent for ambient slideshow loop."""
        with db_session(db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT p.*, v.name as visitor_name
                FROM photos p
                JOIN visitors v ON p.visitor_id = v.id
                WHERE p.consent_display = 1 AND p.is_deleted = 0
                ORDER BY p.uploaded_at DESC
                """
            )
            rows = cur.fetchall()
            return [
                Photo(
                    id=r["id"],
                    visitor_id=r["visitor_id"],
                    filename=r["filename"],
                    original_filename=r["original_filename"],
                    file_size=r["file_size"],
                    mime_type=r["mime_type"],
                    width=r["width"],
                    height=r["height"],
                    consent_display=bool(r["consent_display"]),
                    is_deleted=bool(r["is_deleted"]),
                    visit_number=r["visit_number"],
                    uploaded_at=str(r["uploaded_at"]),
                    visitor_name=r["visitor_name"],
                )
                for r in rows
            ]

    @classmethod
    def verify_pin_and_delete_photo(
        cls, photo_id: int, pin: str, db_path=None
    ) -> bool:
        """Allow visitor to delete their photo if provided PIN matches visitor record."""
        with db_session(db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT p.id, v.pin
                FROM photos p
                JOIN visitors v ON p.visitor_id = v.id
                WHERE p.id = ? AND p.is_deleted = 0
                """,
                (photo_id,),
            )
            row = cur.fetchone()
            if not row:
                return False
            if row["pin"].strip().upper() != (pin or "").strip().upper():
                return False
            
            cur.execute(
                "UPDATE photos SET is_deleted = 1 WHERE id = ?",
                (photo_id,),
            )
            return True
