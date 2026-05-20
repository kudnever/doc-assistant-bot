import unittest

from bot import keyboards


class DocumentsKeyboardTests(unittest.TestCase):
    def test_document_keyboard_exposes_studio_actions_for_document_id(self):
        markup = keyboards.documents_keyboard(
            [{"id": 42, "filename": "contract.pdf"}],
            "en",
        )

        callback_data = [
            button.callback_data
            for row in markup.inline_keyboard
            for button in row
        ]

        self.assertIn("studio:brief:42", callback_data)
        self.assertIn("studio:faq:42", callback_data)
        self.assertIn("studio:quiz:42", callback_data)
        self.assertIn("studio:mindmap:42", callback_data)
        self.assertIn("del:42", callback_data)


if __name__ == "__main__":
    unittest.main()
