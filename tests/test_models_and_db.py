import os
import tempfile
import unittest
from app.database import init_db, db_session
from app.services.visitor_service import VisitorService

class TestModelsAndDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_visitor.db")
        init_db(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_first_time_visitor_creation(self):
        visitor, is_returning = VisitorService.get_or_create_visitor(
            name="Alice Smith",
            secondary_identifier="alice@example.com",
            db_path=self.db_path
        )
        self.assertFalse(is_returning)
        self.assertEqual(visitor.name, "Alice Smith")
        self.assertEqual(visitor.visit_count, 1)
        self.assertEqual(len(visitor.pin), 6)  # 6-char hex PIN

    def test_returning_visitor_detection(self):
        # First visit
        v1, is_returning1 = VisitorService.get_or_create_visitor(
            name="Bob Jones",
            secondary_identifier="+1-555-0199",
            db_path=self.db_path
        )
        self.assertFalse(is_returning1)
        self.assertEqual(v1.visit_count, 1)

        # Second visit with same compound identity
        v2, is_returning2 = VisitorService.get_or_create_visitor(
            name="Bob Jones",
            secondary_identifier="+1-555-0199",
            db_path=self.db_path
        )
        self.assertTrue(is_returning2)
        self.assertEqual(v2.id, v1.id)
        self.assertEqual(v2.visit_count, 2)
        self.assertEqual(v2.pin, v1.pin)

    def test_case_and_whitespace_insensitivity(self):
        v1, _ = VisitorService.get_or_create_visitor(
            name="Carol White",
            secondary_identifier="CAROL@EXAMPLE.COM  ",
            db_path=self.db_path
        )
        v2, is_returning = VisitorService.get_or_create_visitor(
            name="  Carol White ",
            secondary_identifier="carol@example.com",
            db_path=self.db_path
        )
        self.assertTrue(is_returning)
        self.assertEqual(v1.id, v2.id)

    def test_same_name_different_identifier_creates_separate_visitors(self):
        v1, _ = VisitorService.get_or_create_visitor(
            name="David Kim",
            secondary_identifier="david1@gmail.com",
            db_path=self.db_path
        )
        v2, is_returning = VisitorService.get_or_create_visitor(
            name="David Kim",
            secondary_identifier="david2@gmail.com",
            db_path=self.db_path
        )
        self.assertFalse(is_returning)
        self.assertNotEqual(v1.id, v2.id)

if __name__ == "__main__":
    unittest.main()
