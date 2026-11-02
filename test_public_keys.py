import os
import unittest
from unittest.mock import patch

os.environ["KEALEX_DB_HOST"] = ""
os.environ["KEALEX_DB_NAME"] = ""
os.environ["KEALEX_DB_USER"] = ""
os.environ["KEALEX_DB_PASSWORD"] = ""
os.environ["KEALEX_DATABASE_URL"] = "sqlite:///./test.db"
os.environ["KEALEX_SECRET_KEY"] = "public-keys-test-secret"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import Usuario, UsuarioChavePublica, RoleEnum, app, get_db, verify_token


class PublicKeyRouteTests(unittest.TestCase):
    def test_public_key_crud_is_scoped_to_authenticated_user(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Usuario.__table__.create(engine)
        UsuarioChavePublica.__table__.create(engine)
        test_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        with test_session() as db:
            db.add_all([
                Usuario(
                    id="user-1",
                    tenant_id="tenant-1",
                    nome="User 1",
                    email="user1@example.com",
                    senha_hash="hash",
                    role=RoleEnum.advogado,
                    ativo=True,
                ),
                Usuario(
                    id="user-2",
                    tenant_id="tenant-1",
                    nome="User 2",
                    email="user2@example.com",
                    senha_hash="hash",
                    role=RoleEnum.advogado,
                    ativo=True,
                ),
            ])
            db.commit()

        actor = {"id": "user-1"}

        def override_get_db():
            db = test_session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[verify_token] = lambda: {"sub": actor["id"], "tenant_id": "tenant-1"}
        try:
            with patch("app.main._init_db"):
                with TestClient(app) as client:
                    created = client.post("/v1/lex/usuarios/chaves-publicas", json={
                        "orgao": " Justiça Federal ",
                        "chavePublica": " APIKey primeira-chave ",
                    })
                    self.assertEqual(created.status_code, 200)
                    record = created.json()
                    self.assertEqual(record["orgao"], "Justiça Federal")
                    self.assertEqual(record["chavePublica"], "APIKey primeira-chave")

                    updated_by_upsert = client.post("/v1/lex/usuarios/chaves-publicas", json={
                        "orgao": "Justiça Federal",
                        "chavePublica": "APIKey chave-atualizada",
                    })
                    self.assertEqual(updated_by_upsert.status_code, 200)
                    self.assertEqual(updated_by_upsert.json()["id"], record["id"])
                    self.assertEqual(updated_by_upsert.json()["chavePublica"], "APIKey chave-atualizada")

                    listed = client.get("/v1/lex/usuarios/chaves-publicas")
                    self.assertEqual(listed.status_code, 200)
                    self.assertEqual([item["id"] for item in listed.json()], [record["id"]])

                    actor["id"] = "user-2"
                    self.assertEqual(client.get("/v1/lex/usuarios/chaves-publicas").json(), [])
                    self.assertEqual(
                        client.post(f"/v1/lex/usuarios/chaves-publicas/{record['id']}", json={
                            "orgao": "Justiça Federal",
                            "chavePublica": "APIKey não-autorizada",
                        }).status_code,
                        404,
                    )

                    actor["id"] = "user-1"
                    updated = client.post(f"/v1/lex/usuarios/chaves-publicas/{record['id']}", json={
                        "orgao": "Justiça Federal",
                        "chavePublica": "APIKey atualizada",
                    })
                    self.assertEqual(updated.status_code, 200)
                    self.assertEqual(updated.json()["chavePublica"], "APIKey atualizada")

                    alias_listed = client.get("/v1/lex/usuarios/me/chaves-publicas")
                    self.assertEqual(alias_listed.status_code, 200)
                    self.assertEqual(alias_listed.json()[0]["id"], record["id"])

                    deleted = client.delete(f"/v1/lex/usuarios/chaves-publicas/{record['id']}")
                    self.assertEqual(deleted.status_code, 200)
                    self.assertEqual(deleted.json(), {"ok": True})
                    self.assertEqual(client.get("/v1/lex/usuarios/chaves-publicas").json(), [])

                    invalid = client.post("/v1/lex/usuarios/chaves-publicas", json={
                        "orgao": " ",
                        "chavePublica": "chave",
                    })
                    self.assertEqual(invalid.status_code, 422)
        finally:
            app.dependency_overrides.clear()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
