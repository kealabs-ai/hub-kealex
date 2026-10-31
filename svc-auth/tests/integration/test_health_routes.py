import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SERVICE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SERVICE_ROOT))
os.environ.setdefault("KEALEX_DATABASE_URL", "mysql+pymysql://test:test@localhost/test")
os.environ.setdefault("KEALEX_SECRET_KEY", "integration-test-secret")
os.environ.setdefault("KEALEX_ASAAS_BASE_URL", "https://api-sandbox.asaas.com/v3")

from fastapi.testclient import TestClient
from app.main import app


class HealthRouteTests(unittest.TestCase):
    def test_existing_routes_remain_registered(self):
        routes = {
            (route.path, method)
            for route in app.routes
            for method in getattr(route, "methods", set())
        }
        expected = {
            ("/k1/lex/auth/register", "POST"),
            ("/k1/lex/auth/login", "POST"),
            ("/k1/lex/auth/me", "GET"),
            ("/k1/lex/auth/pre-register", "POST"),
            ("/k1/lex/auth/ativar", "POST"),
            ("/k1/lex/auth/assinar", "POST"),
            ("/k1/lex/auth/assinar-pix", "POST"),
            ("/k1/lex/auth/criar-cliente-asaas", "POST"),
            ("/k1/lex/auth/billing-profile", "GET"),
            ("/k1/lex/auth/asaas-webhook", "POST"),
            ("/k1/lex/auth/billing-status", "GET"),
            ("/k1/lex/auth/assinatura/reativar", "POST"),
            ("/k1/lex/auth/assinatura", "GET"),
            ("/health", "GET"),
            ("/k1/lex/health", "GET"),
        }
        self.assertTrue(expected.issubset(routes), expected - routes)

    def test_health_routes_keep_existing_responses(self):
        with patch("app.main._init_db"):
            with TestClient(app) as client:
                self.assertEqual(client.get("/health").json(), {"status": "healthy", "service": "svc-auth"})
                self.assertEqual(client.get("/k1/lex/health").json(), {"status": "ok", "service": "svc-auth"})


if __name__ == "__main__":
    unittest.main()
