import os
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from app import create_app
from app.config import Config
from app.services.slideshow_queue import SlideshowManager
from tests import create_test_image

class TestConcurrencyAndQueue(unittest.TestCase):
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

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_concurrent_uploads_thread_safety(self):
        """Simulate 6 visitors uploading photos concurrently at the same moment."""
        num_workers = 6
        success_list = []
        errors = []

        def worker(visitor_idx):
            try:
                with self.app.test_client() as client:
                    img_buf = create_test_image(format="JPEG", color=(visitor_idx * 30, 100, 150))
                    res = client.post("/api/upload", data={
                        "name": f"Concurrent Visitor {visitor_idx}",
                        "secondary_identifier": f"visitor_{visitor_idx}@concurrent.io",
                        "consent": "true",
                        "photos": (img_buf, f"pic_{visitor_idx}.jpg")
                    }, content_type="multipart/form-data")
                    if res.status_code == 201:
                        success_list.append(res.get_json())
                    else:
                        errors.append(f"Worker {visitor_idx} failed: {res.data}")
            except Exception as e:
                errors.append(f"Worker {visitor_idx} exception: {str(e)}")

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            list(executor.map(worker, range(num_workers)))

        self.assertEqual(len(errors), 0, f"Encountered concurrency errors: {errors}")
        self.assertEqual(len(success_list), num_workers)

    def test_slideshow_queue_priority_ordering(self):
        """Verify new photos receive live priority and FIFO fairness."""
        manager = SlideshowManager()

        # Enqueue Visitor A (1 new photo)
        manager.enqueue_live_upload(
            visitor_name="Visitor A",
            is_returning=False,
            visit_count=1,
            new_photos=[{"id": 1, "url": "/uploads/a1.jpg"}],
            past_photos=[]
        )

        # Enqueue Visitor B (returning: 1 new photo + 1 past photo)
        manager.enqueue_live_upload(
            visitor_name="Visitor B",
            is_returning=True,
            visit_count=2,
            new_photos=[{"id": 2, "url": "/uploads/b_new.jpg"}],
            past_photos=[{"id": 3, "url": "/uploads/b_old.jpg"}]
        )

        # Item 1 should be Visitor A's new photo
        item1 = manager.get_next_priority_item()
        self.assertIsNotNone(item1)
        self.assertEqual(item1["visitor_name"], "Visitor A")
        self.assertTrue(item1["is_new"])

        # Item 2 should be Visitor B's new photo
        item2 = manager.get_next_priority_item()
        self.assertIsNotNone(item2)
        self.assertEqual(item2["visitor_name"], "Visitor B")
        self.assertTrue(item2["is_new"])

        # Item 3 should be Visitor B's past photo
        item3 = manager.get_next_priority_item()
        self.assertIsNotNone(item3)
        self.assertEqual(item3["visitor_name"], "Visitor B")
        self.assertFalse(item3["is_new"])

        # Queue should now be empty
        self.assertIsNone(manager.get_next_priority_item())

if __name__ == "__main__":
    unittest.main()
