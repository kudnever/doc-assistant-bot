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


if __name__ == "__main__":
    unittest.main()
