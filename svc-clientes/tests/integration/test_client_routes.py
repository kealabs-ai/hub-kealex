import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SERVICE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SERVICE_ROOT))
os.environ.setdefault("KEALEX_DATABASE_URL", "mysql+pymysql://test:test@localhost/test")
os.environ.setdefault("KEALEX_SECRET_KEY", "integration-test-secret")

from fastapi.testclient import TestClient
from app.main import app


class ClientRouteTests(unittest.TestCase):
    def test_health_response_is_preserved(self):
        with patch("app.main.initialize_database"):
            with TestClient(app) as client:
                response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "svc-clientes"})

    def test_existing_client_routes_remain_registered(self):
        routes = {
            (route.path, method)
            for route in app.routes
            for method in getattr(route, "methods", set())
        }
        expected = {
            ("/health", "GET"),
            ("/v1/lex/clientes", "GET"),
            ("/v1/lex/clientes/get", "POST"),
            ("/v1/lex/clientes", "POST"),
            ("/v1/lex/clientes/update", "POST"),
            ("/v1/lex/clientes/delete", "POST"),
        }
        self.assertTrue(expected.issubset(routes), expected - routes)


if __name__ == "__main__":
    unittest.main()
