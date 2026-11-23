import os
import tempfile
import unittest
from app import create_app
from app.config import Config
from tests import create_test_image

class TestPrivacyAndConsent(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.upload_dir = os.path.join(self.temp_dir.name, "uploads")
        self.db_path = os.path.join(self.temp_dir.name, "test.db")
        os.makedirs(self.upload_dir, exist_ok=True)

        class TestConfig(Config):
            TESTING = True
            DATABASE_PATH = self.db_path
            UPLOAD_FOLDER = self.upload_dir

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_unconsented_photo_excluded_from_public_slideshow(self):
        # 1. Visitor opts OUT of public display (consent = false)
        img_buf = create_test_image(format="JPEG")
        res = self.client.post("/api/upload", data={
            "name": "Private Visitor",
            "secondary_identifier": "private@privacy.org",
            "consent": "false",
            "photos": (img_buf, "private_pic.jpg")
        }, content_type="multipart/form-data")

        self.assertEqual(res.status_code, 201)
        json_data = res.get_json()
        self.assertFalse(json_data["consent_display"])
        self.assertIn("not displayed on public screens", json_data["message"])

        # 2. Check public slideshow pool - should be EMPTY!
        slideshow_res = self.client.get("/api/slideshow/all")
        slideshow_data = slideshow_res.get_json()
        self.assertEqual(slideshow_data["count"], 0)
        self.assertEqual(len(slideshow_data["photos"]), 0)

    def test_consented_photo_included_in_public_slideshow(self):
        img_buf = create_test_image(format="JPEG")
        self.client.post("/api/upload", data={
            "name": "Public Visitor",
            "secondary_identifier": "public@open.org",
            "consent": "true",
            "photos": (img_buf, "public_pic.jpg")
        }, content_type="multipart/form-data")

        slideshow_res = self.client.get("/api/slideshow/all")
        slideshow_data = slideshow_res.get_json()
        self.assertEqual(slideshow_data["count"], 1)
        self.assertEqual(slideshow_data["photos"][0]["visitor_name"], "Public Visitor")

    def test_self_service_deletion_with_pin(self):
        img_buf = create_test_image(format="JPEG")
        upload_res = self.client.post("/api/upload", data={
            "name": "Remorseful Visitor",
            "secondary_identifier": "delete_me@test.com",
            "consent": "true",
            "photos": (img_buf, "pic.jpg")
        }, content_type="multipart/form-data")

        upload_data = upload_res.get_json()
        photo_id = upload_data["new_photos"][0]["id"]
        pin = upload_data["pin"]

        # Attempt deletion with WRONG PIN -> 403 Forbidden
        del_bad = self.client.post("/api/photos/delete", json={
            "photo_id": photo_id,
            "pin": "WRONG1"
        })
        self.assertEqual(del_bad.status_code, 403)

        # Attempt deletion with CORRECT PIN -> 200 OK
        del_good = self.client.post("/api/photos/delete", json={
            "photo_id": photo_id,
            "pin": pin
        })
        self.assertEqual(del_good.status_code, 200)

        # Verify photo is no longer in public slideshow
        slideshow_res = self.client.get("/api/slideshow/all")
        self.assertEqual(slideshow_res.get_json()["count"], 0)

if __name__ == "__main__":
    unittest.main()
