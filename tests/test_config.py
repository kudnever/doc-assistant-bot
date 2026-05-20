import unittest

from bot.config import settings


class ConfigTests(unittest.TestCase):
    def test_default_chunk_cap_accepts_long_reference_documents(self):
        self.assertGreaterEqual(settings.max_chunks_per_doc, 1000)


if __name__ == "__main__":
    unittest.main()
