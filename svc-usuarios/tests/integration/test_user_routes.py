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


class UserRouteTests(unittest.TestCase):
    def test_health_response_is_preserved(self):
        with patch("app.main.initialize_database"):
            with TestClient(app) as client:
                response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "svc-usuarios"})

    def test_existing_user_and_public_key_routes_remain_registered(self):
        routes = {
            (route.path, method)
            for route in app.routes
            for method in getattr(route, "methods", set())
        }
        expected = {
            ("/health", "GET"),
            ("/v1/lex/usuarios", "GET"),
            ("/v1/lex/usuarios/list", "POST"),
            ("/v1/lex/usuarios/get", "POST"),
            ("/v1/lex/usuarios", "POST"),
            ("/v1/lex/usuarios/update", "POST"),
            ("/v1/lex/usuarios/delete", "POST"),
            ("/v1/lex/usuarios/modalidade", "POST"),
            ("/v1/lex/usuarios/consultas/datajud", "POST"),
            ("/v1/lex/usuarios/chaves-publicas", "GET"),
            ("/v1/lex/usuarios/me/chaves-publicas", "GET"),
            ("/v1/lex/usuarios/chaves-publicas", "POST"),
            ("/v1/lex/usuarios/me/chaves-publicas", "POST"),
            ("/v1/lex/usuarios/chaves-publicas/{key_id}", "POST"),
            ("/v1/lex/usuarios/me/chaves-publicas/{key_id}", "POST"),
            ("/v1/lex/usuarios/chaves-publicas/{key_id}", "DELETE"),
            ("/v1/lex/usuarios/me/chaves-publicas/{key_id}", "DELETE"),
            ("/v1/lex/usuarios/me", "GET"),
        }
        self.assertTrue(expected.issubset(routes), expected - routes)


if __name__ == "__main__":
    unittest.main()
