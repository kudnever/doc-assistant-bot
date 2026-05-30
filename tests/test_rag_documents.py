import tempfile
import unittest
from pathlib import Path

from bot import rag
from bot.config import settings
from bot.db import get_conn, init_schema


class DocumentContextTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._old_db_path = settings.db_path
        settings.db_path = str(Path(self._tmpdir.name) / "bot.db")
        conn = get_conn()
        try:
            init_schema(conn)
            with conn:
                older = conn.execute(
                    "INSERT INTO documents (user_id, filename, uploaded_at) VALUES (?, ?, ?)",
                    (10, "older.txt", "2026-05-18T10:00:00+00:00"),
                ).lastrowid
                latest = conn.execute(
                    "INSERT INTO documents (user_id, filename, uploaded_at) VALUES (?, ?, ?)",
                    (10, "latest.txt", "2026-05-19T10:00:00+00:00"),
                ).lastrowid
                other_user = conn.execute(
                    "INSERT INTO documents (user_id, filename, uploaded_at) VALUES (?, ?, ?)",
                    (99, "private.txt", "2026-05-20T10:00:00+00:00"),
                ).lastrowid
                for idx, text in enumerate(("old one", "old two"), start=1):
                    conn.execute(
                        "INSERT INTO chunks (document_id, idx, text) VALUES (?, ?, ?)",
                        (older, idx, text),
                    )
                for idx, text in enumerate(("latest one", "latest two", "latest three"), start=1):
                    conn.execute(
                        "INSERT INTO chunks (document_id, idx, text) VALUES (?, ?, ?)",
                        (latest, idx, text),
                    )
                conn.execute(
                    "INSERT INTO chunks (document_id, idx, text) VALUES (?, ?, ?)",
                    (other_user, 1, "other user secret"),
                )
            self.older_id = older
            self.latest_id = latest
            self.other_user_id = other_user
        finally:
            conn.close()

    def tearDown(self):
        settings.db_path = self._old_db_path
        self._tmpdir.cleanup()

    def test_latest_document_context_defaults_to_current_users_newest_document(self):
        context = rag.get_document_context(user_id=10)

        self.assertIsNotNone(context)
        self.assertEqual(context["document"]["id"], self.latest_id)
        self.assertEqual(context["document"]["filename"], "latest.txt")
        self.assertEqual([chunk["text"] for chunk in context["chunks"]], [
            "latest one",
            "latest two",
            "latest three",
        ])

    def test_document_context_can_target_specific_owned_document(self):
        context = rag.get_document_context(user_id=10, document_id=self.older_id, max_chunks=1)

        self.assertIsNotNone(context)
        self.assertEqual(context["document"]["id"], self.older_id)
        self.assertEqual([chunk["text"] for chunk in context["chunks"]], ["old one"])

    def test_document_context_rejects_other_users_document(self):
        context = rag.get_document_context(user_id=10, document_id=self.other_user_id)

        self.assertIsNone(context)


if __name__ == "__main__":
    unittest.main()
