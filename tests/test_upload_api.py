import io
import os
import tempfile
import unittest
from app import create_app
from app.config import Config
from tests import create_test_image

class TestUploadAPI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.upload_dir = os.path.join(self.temp_dir.name, "uploads")
        self.db_path = os.path.join(self.temp_dir.name, "test.db")
        os.makedirs(self.upload_dir, exist_ok=True)

        class TestConfig(Config):
            TESTING = True
            DATABASE_PATH = self.db_path
            UPLOAD_FOLDER = self.upload_dir
            MAX_FILES_PER_UPLOAD = 3

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_upload_success_first_visit(self):
        img_buf = create_test_image(format="JPEG")
        data = {
            "name": "Sarah Connor",
            "secondary_identifier": "sarah@resistance.org",
            "consent": "true",
            "photos": (img_buf, "selfie.jpg")
        }
        res = self.client.post("/api/upload", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 201)
        json_data = res.get_json()
        self.assertTrue(json_data["success"])
        self.assertFalse(json_data["is_returning"])
        self.assertEqual(json_data["visit_count"], 1)
        self.assertEqual(len(json_data["new_photos"]), 1)
        self.assertTrue(len(json_data["pin"]) == 6)

    def test_upload_returning_visitor_includes_past_photos(self):
        # 1st Visit
        img_buf1 = create_test_image(format="JPEG", color=(255, 0, 0))
        self.client.post("/api/upload", data={
            "name": "John Doe",
            "secondary_identifier": "john@doe.com",
            "consent": "true",
            "photos": (img_buf1, "first_trip.jpg")
        }, content_type="multipart/form-data")

        # 2nd Visit
        img_buf2 = create_test_image(format="JPEG", color=(0, 255, 0))
        res = self.client.post("/api/upload", data={
            "name": "John Doe",
            "secondary_identifier": "john@doe.com",
            "consent": "true",
            "photos": (img_buf2, "second_trip.jpg")
        }, content_type="multipart/form-data")

        self.assertEqual(res.status_code, 201)
        json_data = res.get_json()
        self.assertTrue(json_data["is_returning"])
        self.assertEqual(json_data["visit_count"], 2)
        self.assertEqual(len(json_data["new_photos"]), 1)
        # Should contain 1 past photo from visit #1!
        self.assertEqual(len(json_data["past_photos"]), 1)
        self.assertIn("past photos are playing", json_data["message"])

    def test_missing_name_returns_400(self):
        img_buf = create_test_image(format="JPEG")
        res = self.client.post("/api/upload", data={
            "name": "",
            "secondary_identifier": "user@mail.com",
            "photos": (img_buf, "test.jpg")
        }, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        self.assertIn("name is required", res.get_json()["error"].lower())

    def test_missing_secondary_identifier_returns_400(self):
        img_buf = create_test_image(format="JPEG")
        res = self.client.post("/api/upload", data={
            "name": "No Email Guy",
            "secondary_identifier": "",
            "photos": (img_buf, "test.jpg")
        }, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        self.assertIn("secondary identifier", res.get_json()["error"].lower())

    def test_too_many_files_rejected(self):
        # Config has MAX_FILES_PER_UPLOAD = 3
        files = [
            (create_test_image(), f"test_{i}.jpg")
            for i in range(4)
        ]
        data = {
            "name": "Spam Uploader",
            "secondary_identifier": "spam@example.com",
            "photos": files
        }
        res = self.client.post("/api/upload", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        self.assertIn("Too many files", res.get_json()["error"])

if __name__ == "__main__":
    unittest.main()
