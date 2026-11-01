import unittest

from fastapi import HTTPException

from app.application.use_cases.ai_catalog import _validate_model_provider


class AiCatalogTests(unittest.TestCase):
    def test_accepts_model_from_matching_provider(self):
        _validate_model_provider("openai", "gpt-4o")

    def test_rejects_model_from_different_provider(self):
        with self.assertRaises(HTTPException) as error:
            _validate_model_provider("openai", "claude-3")

        self.assertEqual(error.exception.status_code, 400)
