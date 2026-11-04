import json
import os
import unittest
from unittest.mock import patch

os.environ["KEALEX_DB_HOST"] = ""
os.environ["KEALEX_DB_NAME"] = ""
os.environ["KEALEX_DB_USER"] = ""
os.environ["KEALEX_DB_PASSWORD"] = ""
os.environ["KEALEX_DATABASE_URL"] = "sqlite:///./test.db"
os.environ["KEALEX_SECRET_KEY"] = "google-drive-route-test-secret"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import auth_guard
from app.infrastructure.database.models.analysis_model import (
    AnaliseConversa,
    AnaliseDocumento,
    Base,
    GoogleDriveCredential,
)
from app.infrastructure.database.session import get_db
from app.main import app


class GoogleDriveRouteTests(unittest.TestCase):
    def test_profile_credentials_upload_and_cleanup_are_owner_scoped(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        test_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        actor = {"id": "user-1", "tenant_id": "tenant-1"}

        def override_get_db():
            db = test_session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[auth_guard] = lambda: {
            "sub": actor["id"],
            "tenant_id": actor["tenant_id"],
            "role": "advogado",
        }
        credentials = {
            "type": "authorized_user",
            "client_id": "client-id",
            "client_secret": "client-secret",
            "refresh_token": "do-not-return-this-token",
        }
        try:
            with patch.object(Base.metadata, "create_all"):
                with TestClient(app) as client:
                    base = "/k1/lex/analise-documentos"
                    config_path = f"{base}/configuracoes/google-drive"
                    self.assertEqual(client.get(config_path).json()["configurado"], False)

                    saved = client.put(config_path, json={
                        "credential_json": json.dumps(credentials),
                        "drive_folder_id": "folder-1",
                    })
                    self.assertEqual(saved.status_code, 200)
                    self.assertEqual(saved.json()["tipo"], "authorized_user")
                    self.assertEqual(saved.json()["driveFolderId"], "folder-1")
                    self.assertNotIn("do-not-return-this-token", saved.text)
                    with test_session() as db:
                        stored = db.query(GoogleDriveCredential).one()
                        self.assertNotIn("do-not-return-this-token", stored.encrypted_credentials)

                    with patch("app.api.routes.document_analysis_routes.GoogleDriveClient.test_connection", return_value={
                        "email": "drive@example.com",
                        "displayName": "Drive Test",
                    }):
                        tested = client.post(f"{config_path}/testar")
                    self.assertEqual(tested.status_code, 200)
                    self.assertEqual(tested.json()["email"], "drive@example.com")

                    conversation = client.post(f"{base}/conversas", json={})
                    self.assertEqual(conversation.status_code, 201)
                    conversation_id = conversation.json()["id"]
                    with patch("app.api.routes.document_analysis_routes.GoogleDriveClient.upload", return_value={
                        "id": "drive-file-1",
                        "webViewLink": "https://drive.google.com/file/d/drive-file-1",
                    }) as drive_upload:
                        uploaded = client.post(
                            f"{base}/conversas/{conversation_id}/documentos",
                            files={"file": ("contrato.txt", b"Conteudo juridico do contrato.", "text/plain")},
                        )
                    self.assertEqual(uploaded.status_code, 201)
                    self.assertEqual(uploaded.json()["driveUrl"], "https://drive.google.com/file/d/drive-file-1")
                    drive_upload.assert_called_once()
                    with test_session() as db:
                        stored_document = db.query(AnaliseDocumento).one()
                        self.assertEqual(stored_document.drive_file_id, "drive-file-1")

                    changed_credentials = {**credentials, "refresh_token": "new-refresh-token"}
                    changed = client.put(config_path, json={
                        "credential_json": json.dumps(changed_credentials),
                        "drive_folder_id": "folder-2",
                    })
                    self.assertEqual(changed.status_code, 409)

                    with patch("app.api.routes.document_analysis_routes.GoogleDriveClient.delete") as drive_delete:
                        deleted_document = client.delete(
                            f"{base}/conversas/{conversation_id}/documentos/{uploaded.json()['id']}"
                        )
                    self.assertEqual(deleted_document.status_code, 200)
                    drive_delete.assert_called_once_with("drive-file-1")

                    changed = client.put(config_path, json={
                        "credential_json": json.dumps(changed_credentials),
                        "drive_folder_id": "folder-2",
                    })
                    self.assertEqual(changed.status_code, 200)

                    actor["id"] = "user-2"
                    self.assertEqual(client.get(config_path).json()["configurado"], False)
                    self.assertEqual(client.delete(config_path).status_code, 400)
        finally:
            app.dependency_overrides.clear()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
