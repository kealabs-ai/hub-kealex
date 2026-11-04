import base64
import json
import os
import unittest
from urllib.parse import parse_qs
from unittest.mock import patch

os.environ.setdefault("KEALEX_SECRET_KEY", "google-drive-test-secret")

from app.infrastructure.google_drive import (
    GOOGLE_DRIVE_UPLOAD_API,
    GoogleDriveClient,
    GoogleDriveError,
    decrypt_credentials,
    encrypt_credentials,
    validate_credentials_json,
)


class FakeResponse:
    def __init__(self, value):
        self.value = json.dumps(value).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.value


class GoogleDriveTests(unittest.TestCase):
    def setUp(self):
        self.credentials = json.dumps({
            "type": "authorized_user",
            "client_id": "client-id",
            "client_secret": "client-secret",
            "refresh_token": "refresh-token",
        })

    def test_credentials_are_encrypted_and_never_returned_as_plaintext(self):
        encrypted = encrypt_credentials(self.credentials)

        self.assertNotIn("refresh-token", encrypted)
        self.assertEqual(decrypt_credentials(encrypted), self.credentials)

    def test_credential_validation_rejects_unknown_auth_types(self):
        with self.assertRaisesRegex(ValueError, "OAuth de usuário"):
            validate_credentials_json('{"type":"unknown"}')

    def test_upload_refreshes_oauth_token_and_sends_file_to_drive(self):
        client = GoogleDriveClient(self.credentials, "folder-123")
        responses = [
            FakeResponse({"access_token": "access-token"}),
            FakeResponse({"id": "drive-file-1", "webViewLink": "https://drive.google.com/file/d/drive-file-1"}),
        ]
        with patch("app.infrastructure.google_drive.urlopen", side_effect=responses) as mocked_urlopen:
            result = client.upload("contrato.txt", "text/plain", b"texto juridico")

        self.assertEqual(result["id"], "drive-file-1")
        self.assertEqual(result["webViewLink"], "https://drive.google.com/file/d/drive-file-1")
        upload_request = mocked_urlopen.call_args_list[1].args[0]
        self.assertTrue(upload_request.full_url.startswith(GOOGLE_DRIVE_UPLOAD_API))
        self.assertIn(b'"parents": ["folder-123"]', upload_request.data)
        self.assertIn(b"texto juridico", upload_request.data)
        self.assertEqual(upload_request.get_header("Authorization"), "Bearer access-token")

    def test_service_account_generates_scoped_jwt_assertion(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("ascii")
        service_account = json.dumps({
            "type": "service_account",
            "client_email": "drive-service@example.iam.gserviceaccount.com",
            "private_key": private_key_pem,
        })
        client = GoogleDriveClient(service_account)
        responses = [
            FakeResponse({"access_token": "service-access-token"}),
            FakeResponse({"user": {"emailAddress": "drive-service@example.iam.gserviceaccount.com"}}),
        ]
        with patch("app.infrastructure.google_drive.urlopen", side_effect=responses) as mocked_urlopen:
            account = client.test_connection()

        form = parse_qs(mocked_urlopen.call_args_list[0].args[0].data.decode("ascii"))
        assertion = form["assertion"][0].split(".")
        claims = json.loads(base64.urlsafe_b64decode(assertion[1] + "=" * (-len(assertion[1]) % 4)))
        self.assertEqual(claims["scope"], "https://www.googleapis.com/auth/drive.file")
        self.assertEqual(claims["iss"], "drive-service@example.iam.gserviceaccount.com")
        self.assertEqual(account["email"], "drive-service@example.iam.gserviceaccount.com")

    def test_invalid_json_is_reported_without_echoing_credentials(self):
        with self.assertRaisesRegex(ValueError, "JSON válido"):
            validate_credentials_json("not-json")

    def test_oauth_http_errors_do_not_expose_provider_response(self):
        from urllib.error import HTTPError

        client = GoogleDriveClient(self.credentials)
        error = HTTPError(
            "https://oauth2.googleapis.com/token",
            400,
            "invalid_grant refresh-token-value",
            hdrs=None,
            fp=None,
        )
        with patch("app.infrastructure.google_drive.urlopen", side_effect=error):
            with self.assertRaisesRegex(GoogleDriveError, "O Google recusou as credenciais") as raised:
                client.test_connection()
        self.assertNotIn("refresh-token-value", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
