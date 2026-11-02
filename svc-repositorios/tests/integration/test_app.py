import os
import unittest
from unittest.mock import patch

os.environ["KEALEX_DATABASE_URL"] = "sqlite:///./integration_test.db"
os.environ["KEALEX_SECRET_KEY"] = "integration-test-secret"

from fastapi.testclient import TestClient

from app.main import app
from app.infrastructure.database.models.repository_model import Base


class AppIntegrationTests(unittest.TestCase):
    def test_health_and_existing_repository_routes(self):
        with patch.object(Base.metadata, "create_all"):
            with TestClient(app) as client:
                response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "svc-repositorios"})
        paths = {route.path for route in app.routes}
        self.assertIn("/k1/lex/repositorios", paths)
        self.assertIn("/k1/lex/repositorios/{repo_id}/upload", paths)
        self.assertIn("/k1/lex/repositorios/{repo_id}/scan", paths)


if __name__ == "__main__":
    unittest.main()
