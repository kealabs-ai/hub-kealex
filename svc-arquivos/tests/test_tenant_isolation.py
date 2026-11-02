import os
import tempfile
import unittest
from uuid import uuid4

os.environ.setdefault("KEALEX_SECRET_KEY", "test-secret-not-for-production")

from fastapi.testclient import TestClient
from jose import jwt
from app import main


class TenantFileIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        main.UPLOAD_DIR = __import__("pathlib").Path(self.temp_dir.name)
        self.client = TestClient(main.app)
        self.tenant_a, self.user_a = str(uuid4()), str(uuid4())
        self.tenant_b, self.user_b = str(uuid4()), str(uuid4())

    def tearDown(self):
        self.temp_dir.cleanup()

    def token(self, tenant, user):
        return jwt.encode({"tenant_id": tenant, "sub": user}, main.SECRET, algorithm="HS256")

    def test_other_tenant_cannot_download_or_delete_file(self):
        a = {"Authorization": f"Bearer {self.token(self.tenant_a, self.user_a)}"}
        b = {"Authorization": f"Bearer {self.token(self.tenant_b, self.user_b)}"}
        upload = self.client.post("/v1/lex/arquivos", headers=a, files={"file": ("case.txt", b"private")})
        self.assertEqual(upload.status_code, 201)
        file_id = upload.json()["id"]
        self.assertEqual(self.client.get(f"/v1/lex/arquivos/{file_id}", headers=b).status_code, 404)
        self.assertEqual(self.client.delete(f"/v1/lex/arquivos/{file_id}", headers=b).status_code, 404)
        self.assertEqual(self.client.get(f"/v1/lex/arquivos/{file_id}", headers=a).content, b"private")


if __name__ == "__main__":
    unittest.main()
