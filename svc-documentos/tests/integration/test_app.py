import os
import unittest
from unittest.mock import patch

os.environ["KEALEX_DATABASE_URL"] = "mysql+pymysql://user:password@localhost/test"
os.environ["KEALEX_SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient

from app.infrastructure.database.models.document_model import Base
from app.main import app


class AppIntegrationTests(unittest.TestCase):
    def test_health_and_document_routes(self):
        with patch.object(Base.metadata, "create_all"):
            with TestClient(app) as client:
                response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "svc-documentos"})

        paths = {route.path for route in app.routes}
        self.assertIn("/v1/lex/documentos", paths)
        self.assertIn("/k1/lex/analise-documentos/conversas", paths)
