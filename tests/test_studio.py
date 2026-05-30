import unittest

from bot import studio


class StudioTests(unittest.TestCase):
    def test_build_prompt_names_the_requested_artifact_and_requires_sources(self):
        prompt = studio.build_prompt(
            "faq",
            "en",
            {"filename": "policy.pdf"},
            [{"idx": 1, "text": "Refunds are available within 14 days."}],
        )

        self.assertIn("FAQ", prompt)
        self.assertIn("policy.pdf", prompt)
        self.assertIn("[1]", prompt)
        self.assertIn("only the numbered source chunks", prompt)

    def test_parse_quiz_json_accepts_valid_questions(self):
        raw = """
        {
          "questions": [
            {
              "question": "What is the refund period?",
              "options": ["7 days", "14 days", "30 days"],
              "answer_index": 1,
              "explanation": "The source states 14 days.",
              "citation": "[1]"
            }
          ]
        }
        """

        questions = studio.parse_quiz_json(raw)

        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["answer_index"], 1)
        self.assertEqual(questions[0]["options"][1], "14 days")

    def test_parse_quiz_json_rejects_invalid_answer_index(self):
        raw = """
        {
          "questions": [
            {
              "question": "Pick one",
              "options": ["A", "B"],
              "answer_index": 4,
              "explanation": "Bad index",
              "citation": "[1]"
            }
          ]
        }
        """

        with self.assertRaises(ValueError):
            studio.parse_quiz_json(raw)

    def test_fallback_overview_uses_document_chunks_without_llm(self):
        text = studio.fallback_overview(
            {"filename": "manual.pdf"},
            [
                {"idx": 1, "text": "First topic explains demand and supply. It includes examples."},
                {"idx": 2, "text": "Second topic explains inflation, money, and prices."},
            ],
        )

        self.assertIn("manual.pdf", text)
        self.assertIn("First topic explains demand and supply.", text)
        self.assertIn("/brief", text)


if __name__ == "__main__":
    unittest.main()
