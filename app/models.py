from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

@dataclass
class Visitor:
    id: int
    name: str
    secondary_identifier: str
    pin: str
    visit_count: int
    created_at: str
    last_visit_at: str

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "secondary_identifier": self.secondary_identifier,
            "visit_count": self.visit_count,
            "created_at": self.created_at,
            "last_visit_at": self.last_visit_at,
            "is_returning": self.visit_count > 1
        }

@dataclass
class Photo:
    id: int
    visitor_id: int
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    width: Optional[int]
    height: Optional[int]
    consent_display: bool
    is_deleted: bool
    visit_number: int
    uploaded_at: str
    visitor_name: Optional[str] = None

    def to_dict(self):
        return {
            "id": self.id,
            "visitor_id": self.visitor_id,
            "visitor_name": self.visitor_name,
            "filename": self.filename,
            "url": f"/uploads/{self.filename}",
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "width": self.width,
            "height": self.height,
            "consent_display": bool(self.consent_display),
            "visit_number": self.visit_number,
            "uploaded_at": self.uploaded_at
        }
