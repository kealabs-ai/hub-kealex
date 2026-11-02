import os
import unittest
from unittest.mock import patch

os.environ["KEALEX_DB_HOST"] = ""
os.environ["KEALEX_DB_NAME"] = ""
os.environ["KEALEX_DB_USER"] = ""
os.environ["KEALEX_DB_PASSWORD"] = ""
os.environ["KEALEX_DATABASE_URL"] = "mysql+pymysql://test:test@localhost/test"
os.environ["KEALEX_SECRET_KEY"] = "intimacoes-test-secret"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import Intimacao, app
from app.main import Base, get_db, verify_token


class IntimacaoRouteTests(unittest.TestCase):
    def test_intimacao_crud_is_tenant_scoped(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Intimacao.__table__.create(engine)
        test_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        current_tenant = {"id": "tenant-1"}

        def override_get_db():
            db = test_session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[verify_token] = lambda: {
            "sub": "user-1",
            "tenant_id": current_tenant["id"],
        }
        try:
            with patch("app.main._init_db"):
                with TestClient(app) as client:
                    created = client.post("/intimacoes", json={
                        "processoNumero": "0001234-56.2026.8.00.0001",
                        "processoTitulo": "Ação de cobrança",
                        "diario": "DJE",
                        "dataPublicacao": "2026-11-02",
                        "conteudo": "Publicação para manifestação.",
                    })
                    self.assertEqual(created.status_code, 201)
                    record = created.json()
                    self.assertEqual(record["status"], "nova")
                    self.assertEqual(record["diario"], "DJE")

                    listed = client.get("/intimacoes")
                    self.assertEqual(listed.status_code, 200)
                    self.assertEqual([item["id"] for item in listed.json()], [record["id"]])

                    updated = client.patch(f"/intimacoes/{record['id']}", json={"status": "lida"})
                    self.assertEqual(updated.status_code, 200)
                    self.assertEqual(updated.json()["status"], "lida")

                    current_tenant["id"] = "tenant-2"
                    self.assertEqual(client.get("/intimacoes").json(), [])
                    self.assertEqual(
                        client.patch(f"/intimacoes/{record['id']}", json={"status": "respondida"}).status_code,
                        404,
                    )

                    current_tenant["id"] = "tenant-1"
                    deleted = client.delete(f"/intimacoes/{record['id']}")
                    self.assertEqual(deleted.status_code, 200)
                    self.assertEqual(deleted.json(), {"ok": True})
                    self.assertEqual(client.get("/intimacoes").json(), [])
        finally:
            app.dependency_overrides.clear()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
