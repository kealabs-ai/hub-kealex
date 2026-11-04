import base64
import hashlib
import json
import os
import time
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

from cryptography.fernet import Fernet, InvalidToken

GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_API = "https://www.googleapis.com/drive/v3"
GOOGLE_DRIVE_UPLOAD_API = "https://www.googleapis.com/upload/drive/v3/files"
GOOGLE_DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"


class GoogleDriveError(Exception):
    pass


def _fernet() -> Fernet:
    key = os.getenv("KEALEX_GOOGLE_DRIVE_ENCRYPTION_KEY")
    if key:
        try:
            return Fernet(key.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as exc:
            raise RuntimeError("KEALEX_GOOGLE_DRIVE_ENCRYPTION_KEY deve ser uma chave Fernet válida.") from exc

    secret = os.getenv("KEALEX_SECRET_KEY") or os.getenv("KEALEX_JWT_SECRET")
    if not secret:
        raise RuntimeError("Configure KEALEX_SECRET_KEY ou KEALEX_JWT_SECRET para proteger credenciais do Google Drive.")
    derived = base64.urlsafe_b64encode(
        hashlib.sha256((secret + ":google-drive-credentials:v1").encode("utf-8")).digest()
    )
    return Fernet(derived)


def validate_credentials_json(value: str) -> dict[str, Any]:
    try:
        credentials = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("As credenciais devem estar em formato JSON válido.") from exc
    if not isinstance(credentials, dict):
        raise ValueError("As credenciais devem ser um objeto JSON.")

    credential_type = credentials.get("type")
    if credential_type == "service_account":
        if not credentials.get("client_email") or not credentials.get("private_key"):
            raise ValueError("A credencial de conta de serviço precisa conter client_email e private_key.")
        if credentials.get("token_uri", GOOGLE_TOKEN_URI) != GOOGLE_TOKEN_URI:
            raise ValueError("A URL de autenticação informada não é aceita.")
    elif credential_type == "authorized_user":
        required = ("client_id", "client_secret", "refresh_token")
        if any(not credentials.get(field) for field in required):
            raise ValueError("A credencial OAuth precisa conter client_id, client_secret e refresh_token.")
        if credentials.get("token_uri", GOOGLE_TOKEN_URI) != GOOGLE_TOKEN_URI:
            raise ValueError("A URL de autenticação informada não é aceita.")
    else:
        raise ValueError("Use JSON OAuth de usuário autorizado ou JSON de conta de serviço do Google.")
    return credentials


def encrypt_credentials(value: str) -> str:
    validate_credentials_json(value)
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_credentials(value: str) -> str:
    try:
        decrypted = _fernet().decrypt(value.encode("ascii")).decode("utf-8")
        validate_credentials_json(decrypted)
        return decrypted
    except (InvalidToken, ValueError, UnicodeDecodeError) as exc:
        raise GoogleDriveError(
            "Não foi possível descriptografar a conexão do Google Drive. Verifique a chave de criptografia configurada."
        ) from exc


class GoogleDriveClient:
    def __init__(self, credentials_json: str, folder_id: str | None = None):
        try:
            self.credentials = validate_credentials_json(credentials_json)
        except ValueError as exc:
            raise GoogleDriveError(str(exc)) from exc
        self.folder_id = folder_id.strip() if folder_id and folder_id.strip() else None

    def _access_token(self) -> str:
        credentials = self.credentials
        if credentials["type"] == "authorized_user":
            body = urlencode({
                "client_id": credentials["client_id"],
                "client_secret": credentials["client_secret"],
                "refresh_token": credentials["refresh_token"],
                "grant_type": "refresh_token",
            }).encode("utf-8")
        else:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding

            now = int(time.time())
            header = {"alg": "RS256", "typ": "JWT"}
            claims = {
                "iss": credentials["client_email"],
                "scope": GOOGLE_DRIVE_SCOPE,
                "aud": GOOGLE_TOKEN_URI,
                "iat": now,
                "exp": now + 3600,
            }
            encoded_header = base64.urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode()).rstrip(b"=")
            encoded_claims = base64.urlsafe_b64encode(json.dumps(claims, separators=(",", ":")).encode()).rstrip(b"=")
            signing_input = encoded_header + b"." + encoded_claims
            try:
                private_key = serialization.load_pem_private_key(
                    credentials["private_key"].encode("utf-8"),
                    password=None,
                )
                signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
            except (TypeError, ValueError) as exc:
                raise GoogleDriveError("A chave privada da conta de serviço é inválida.") from exc
            assertion = signing_input + b"." + base64.urlsafe_b64encode(signature).rstrip(b"=")
            body = urlencode({
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion.decode("ascii"),
            }).encode("utf-8")

        request = Request(
            GOOGLE_TOKEN_URI,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                token_data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise GoogleDriveError("O Google recusou as credenciais. Confira a configuração e as permissões do Drive.") from exc
        except (URLError, TimeoutError) as exc:
            raise GoogleDriveError("Não foi possível conectar ao serviço de autenticação do Google.") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GoogleDriveError("O serviço de autenticação do Google retornou uma resposta inválida.") from exc
        access_token = token_data.get("access_token") if isinstance(token_data, dict) else None
        if not access_token:
            raise GoogleDriveError("O Google não retornou um token de acesso válido.")
        return access_token

    def _request_json(self, url: str, token: str, data: bytes | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
        request_headers = {"Authorization": f"Bearer {token}"}
        request_headers.update(headers or {})
        request = Request(url, data=data, headers=request_headers, method="POST" if data is not None else "GET")
        try:
            with urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise GoogleDriveError("O Google Drive recusou o acesso. Verifique as permissões e o escopo da credencial.") from exc
            if exc.code == 404:
                raise GoogleDriveError("A pasta configurada não foi encontrada ou não está acessível.") from exc
            raise GoogleDriveError(f"O Google Drive respondeu com erro ({exc.code}).") from exc
        except (URLError, TimeoutError) as exc:
            raise GoogleDriveError("Não foi possível conectar ao Google Drive.") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GoogleDriveError("O Google Drive retornou uma resposta inválida.") from exc
        if not isinstance(result, dict):
            raise GoogleDriveError("O Google Drive retornou uma resposta inválida.")
        return result

    def test_connection(self) -> dict[str, str]:
        token = self._access_token()
        result = self._request_json(
            f"{GOOGLE_DRIVE_API}/about?fields=user(displayName,emailAddress)",
            token,
        )
        user = result.get("user") or {}
        return {
            "email": str(user.get("emailAddress") or ""),
            "displayName": str(user.get("displayName") or ""),
        }

    def upload(self, name: str, content_type: str, content: bytes) -> dict[str, str]:
        token = self._access_token()
        boundary = f"kealex-{uuid.uuid4().hex}"
        metadata: dict[str, Any] = {"name": name}
        if self.folder_id:
            metadata["parents"] = [self.folder_id]
        body = (
            f"--{boundary}\r\n"
            "Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{json.dumps(metadata, ensure_ascii=False)}\r\n"
            f"--{boundary}\r\n"
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8") + content + f"\r\n--{boundary}--".encode("ascii")
        result = self._request_json(
            f"{GOOGLE_DRIVE_UPLOAD_API}?uploadType=multipart&fields=id,name,webViewLink&supportsAllDrives=true",
            token,
            data=body,
            headers={"Content-Type": f"multipart/related; boundary={boundary}"},
        )
        file_id = result.get("id")
        if not file_id:
            raise GoogleDriveError("O Google Drive não confirmou o salvamento do arquivo.")
        return {
            "id": str(file_id),
            "webViewLink": str(result.get("webViewLink") or ""),
        }

    def delete(self, file_id: str) -> None:
        token = self._access_token()
        request = Request(
            f"{GOOGLE_DRIVE_API}/files/{quote(file_id, safe='')}?supportsAllDrives=true",
            headers={"Authorization": f"Bearer {token}"},
            method="DELETE",
        )
        try:
            with urlopen(request, timeout=30):
                pass
        except HTTPError as exc:
            if exc.code != 404:
                raise GoogleDriveError(f"O Google Drive respondeu com erro ({exc.code}) ao remover o arquivo.") from exc
        except (URLError, TimeoutError) as exc:
            raise GoogleDriveError("Não foi possível remover o arquivo do Google Drive.") from exc
