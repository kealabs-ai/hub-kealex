import os
import unittest
from unittest.mock import patch

os.environ.setdefault("KEALEX_DATABASE_URL", "mysql+pymysql://user:password@localhost/test")
os.environ.setdefault("KEALEX_SECRET_KEY", "test-secret")

from fastapi.testclient import TestClient

from app.infrastructure.database.models.cobranca_model import Base
from app.main import app


class AppIntegrationTests(unittest.TestCase):
    def test_health_endpoint_and_existing_route_aliases(self):
        with patch.object(Base.metadata, "create_all"):
            with TestClient(app) as client:
                response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy", "service": "svc-cobrancas"})

        paths = {route.path for route in app.routes}
        self.assertIn("/k1/lex/cobrancas", paths)
        self.assertIn("/v1/lex/cobrancas", paths)
        self.assertIn("/cobrancas", paths)
