import html
import unittest

from bot.i18n import t


class SourceLineFormattingTests(unittest.TestCase):
    def test_source_line_includes_preview_and_is_html_safe(self) -> None:
        rendered = t(
            "source_line",
            "en",
            number=1,
            filename=html.escape("a<b>.txt"),
            idx=7,
            preview=html.escape("line <b>tag</b> & more"),
        )

        self.assertIn("[1] <code>a&lt;b&gt;.txt</code> · chunk 7", rendered)
        self.assertIn("↳ <i>line &lt;b&gt;tag&lt;/b&gt; &amp; more</i>", rendered)


class CrossDocSummaryTests(unittest.TestCase):
    def test_no_summary_when_single_document(self) -> None:
        from bot.handlers import _answer_text

        rendered = _answer_text(
            "ans",
            [{"document_id": 1, "filename": "a.txt", "idx": 1, "text_preview": "p"}],
            "en",
        )
        self.assertNotIn("Across", rendered)

    def test_summary_present_when_multiple_documents(self) -> None:
        from bot.handlers import _answer_text

        rendered = _answer_text(
            "ans",
            [
                {"document_id": 1, "filename": "a.txt", "idx": 1, "text_preview": "p"},
                {"document_id": 2, "filename": "b.txt", "idx": 1, "text_preview": "q"},
            ],
            "en",
        )
        self.assertIn("Across 2 documents", rendered)


if __name__ == "__main__":
    unittest.main()
