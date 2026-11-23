import io
import os
import tempfile
import unittest
from werkzeug.datastructures import FileStorage
from PIL import Image
from app.config import Config
from app.services.image_service import ImageService, ImageValidationError
from tests import create_test_image

class TestImageValidation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_upload_folder = Config.UPLOAD_FOLDER
        Config.UPLOAD_FOLDER = self.temp_dir.name

    def tearDown(self):
        Config.UPLOAD_FOLDER = self.old_upload_folder
        self.temp_dir.cleanup()

    def test_valid_jpeg_processing(self):
        buf = create_test_image(format="JPEG", size=(300, 200))
        file = FileStorage(stream=buf, filename="vacation.jpg", content_type="image/jpeg")

        meta = ImageService.process_and_save_image(file)
        self.assertTrue(meta["filename"].endswith(".jpg"))
        self.assertEqual(meta["width"], 300)
        self.assertEqual(meta["height"], 200)
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir.name, meta["filename"])))

    def test_valid_png_processing(self):
        buf = create_test_image(format="PNG", size=(150, 150))
        file = FileStorage(stream=buf, filename="avatar.png", content_type="image/png")

        meta = ImageService.process_and_save_image(file)
        self.assertTrue(meta["filename"].endswith(".png"))
        self.assertEqual(meta["width"], 150)
        self.assertEqual(meta["height"], 150)

    def test_reject_invalid_extension(self):
        buf = io.BytesIO(b"print('malicious code')")
        file = FileStorage(stream=buf, filename="script.py", content_type="text/x-python")

        with self.assertRaises(ImageValidationError) as ctx:
            ImageService.process_and_save_image(file)
        self.assertIn("Invalid file extension", str(ctx.exception))

    def test_reject_spoofed_file_magic_bytes(self):
        # A file named .jpg but actually containing bash or HTML
        buf = io.BytesIO(b"#!/bin/bash\necho hello world")
        file = FileStorage(stream=buf, filename="attack.jpg", content_type="image/jpeg")

        with self.assertRaises(ImageValidationError) as ctx:
            ImageService.process_and_save_image(file)
        self.assertIn("recognized image signatures", str(ctx.exception))

    def test_reject_empty_file(self):
        buf = io.BytesIO(b"")
        file = FileStorage(stream=buf, filename="empty.jpg", content_type="image/jpeg")

        with self.assertRaises(ImageValidationError) as ctx:
            ImageService.process_and_save_image(file)
        self.assertIn("empty", str(ctx.exception).lower())

    def test_exif_sanitization(self):
        # Image saved by phone camera with simulated EXIF
        buf = io.BytesIO()
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        img.save(buf, format="JPEG")
        buf.seek(0)

        file = FileStorage(stream=buf, filename="photo.jpg", content_type="image/jpeg")
        meta = ImageService.process_and_save_image(file)

        saved_path = os.path.join(self.temp_dir.name, meta["filename"])
        saved_img = Image.open(saved_path)
        
        # Verify saved image has no GPS or personal EXIF data
        exif = saved_img.getexif()
        self.assertEqual(len(exif), 0)

if __name__ == "__main__":
    unittest.main()
