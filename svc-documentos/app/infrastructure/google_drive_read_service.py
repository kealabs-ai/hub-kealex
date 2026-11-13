"""OAuth and read-only Google Drive v3 client for user-owned integrations."""
import base64
import hashlib
import json
import os
import threading
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

from cryptography.fernet import Fernet, InvalidToken

TOKEN_URI = "https://oauth2.googleapis.com/token"
DRIVE_API = "https://www.googleapis.com/drive/v3"
DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
MAX_DOWNLOAD_BYTES = 30 * 1024 * 1024
_ACCESS_TOKEN_CACHE: dict[str, tuple[str, float]] = {}
_ACCESS_TOKEN_LOCK = threading.Lock()


class GoogleDriveIntegrationError(Exception):
    pass


class GoogleDriveReauthenticationRequired(GoogleDriveIntegrationError):
    pass


def _fernet() -> Fernet:
    configured_key = os.getenv("KEALEX_GOOGLE_DRIVE_ENCRYPTION_KEY", "").strip()
    if configured_key:
        try:
            return Fernet(configured_key.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as exc:
            raise RuntimeError("KEALEX_GOOGLE_DRIVE_ENCRYPTION_KEY deve ser uma chave Fernet válida.") from exc
    secret = os.getenv("KEALEX_SECRET_KEY") or os.getenv("KEALEX_JWT_SECRET")
    if not secret:
        raise RuntimeError("Configure uma chave de criptografia para proteger o refresh_token do Google Drive.")
    key = base64.urlsafe_b64encode(hashlib.sha256((secret + ":google-drive-readonly:v1").encode()).digest())
    return Fernet(key)


def encrypt_refresh_token(refresh_token: str) -> str:
    if not refresh_token:
        raise ValueError("O Google não retornou um refresh_token.")
    return _fernet().encrypt(refresh_token.encode("utf-8")).decode("ascii")


def decrypt_refresh_token(encrypted_token: str) -> str:
    try:
        return _fernet().decrypt(encrypted_token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
        raise GoogleDriveIntegrationError("Não foi possível ler a conexão criptografada do Google Drive.") from exc


def _oauth_config() -> tuple[str, str, str]:
    client_id = os.getenv("KEALEX_GOOGLE_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.getenv("KEALEX_GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("KEALEX_GOOGLE_OAUTH_REDIRECT_URI", "").strip()
    if not client_id or not client_secret or not redirect_uri:
        raise GoogleDriveIntegrationError("A autenticação OAuth do Google Drive não está configurada no servidor.")
    return client_id, client_secret, redirect_uri


class GoogleDriveService:
    """Obtains short-lived access tokens and calls Drive using drive.readonly only."""

    def __init__(self, refresh_token: str, client_id: str | None = None, client_secret: str | None = None):
        if not refresh_token:
            raise ValueError("refresh_token obrigatório.")
        default_id, default_secret, _ = _oauth_config()
        self.refresh_token = refresh_token
        self.client_id = client_id or default_id
        self.client_secret = client_secret or default_secret

    def _token(self) -> str:
        cache_key = hashlib.sha256(self.refresh_token.encode()).hexdigest()
        with _ACCESS_TOKEN_LOCK:
            cached = _ACCESS_TOKEN_CACHE.get(cache_key)
            if cached and time.time() < cached[1] - 60:
                return cached[0]
            request = Request(
                TOKEN_URI,
                data=urlencode({
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token",
                }).encode("utf-8"),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            try:
                with urlopen(request, timeout=20) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                if exc.code in (400, 401) and "invalid_grant" in body:
                    _ACCESS_TOKEN_CACHE.pop(cache_key, None)
                    raise GoogleDriveReauthenticationRequired("A autorização do Google foi revogada. Conecte o Drive novamente.") from exc
                raise GoogleDriveIntegrationError(f"O Google recusou a renovação do acesso ({exc.code}).") from exc
            except (URLError, TimeoutError) as exc:
                raise GoogleDriveIntegrationError("Não foi possível conectar à autenticação do Google.") from exc
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise GoogleDriveIntegrationError("O Google retornou uma resposta de autenticação inválida.") from exc
            access_token = payload.get("access_token") if isinstance(payload, dict) else None
            if not access_token:
                raise GoogleDriveIntegrationError("O Google não retornou um access_token válido.")
            expires_at = time.time() + int(payload.get("expires_in") or 3600)
            _ACCESS_TOKEN_CACHE[cache_key] = (str(access_token), expires_at)
            return str(access_token)

    def _request(self, url: str, *, binary: bool = False) -> Any:
        request = Request(url, headers={"Authorization": f"Bearer {self._token()}"})
        try:
            with urlopen(request, timeout=45) as response:
                data = response.read(MAX_DOWNLOAD_BYTES + 1 if binary else -1)
                content_type = response.headers.get("Content-Type", "application/octet-stream")
        except HTTPError as exc:
            if exc.code == 401:
                raise GoogleDriveReauthenticationRequired("A autorização do Google expirou ou foi revogada. Conecte o Drive novamente.") from exc
            if exc.code == 404:
                raise GoogleDriveIntegrationError("O arquivo não existe ou não está acessível nesta conta Google.") from exc
            if exc.code == 403:
                raise GoogleDriveIntegrationError("O Google Drive negou a leitura deste arquivo.") from exc
            raise GoogleDriveIntegrationError(f"O Google Drive respondeu com erro ({exc.code}).") from exc
        except (URLError, TimeoutError) as exc:
            raise GoogleDriveIntegrationError("Não foi possível conectar ao Google Drive.") from exc
        if binary:
            if len(data) > MAX_DOWNLOAD_BYTES:
                raise GoogleDriveIntegrationError("O arquivo ultrapassa o limite de download de 30 MB.")
            return data, content_type
        try:
            result = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GoogleDriveIntegrationError("O Google Drive retornou uma resposta inválida.") from exc
        if not isinstance(result, dict):
            raise GoogleDriveIntegrationError("O Google Drive retornou uma resposta inválida.")
        return result

    def list_files(self, *, query: str | None = None, page_size: int = 50, page_token: str | None = None) -> dict[str, Any]:
        clauses = ["trashed = false"]
        if query and query.strip():
            escaped = query.strip().replace("\\", "\\\\").replace("'", "\\'")
            clauses.append(f"name contains '{escaped}'")
        params: dict[str, str] = {
            "q": " and ".join(clauses),
            "pageSize": str(max(1, min(page_size, 100))),
            "orderBy": "modifiedTime desc",
            "fields": "nextPageToken,files(id,name,mimeType,size,modifiedTime,webViewLink)",
        }
        if page_token:
            params["pageToken"] = page_token
        result = self._request(f"{DRIVE_API}/files?{urlencode(params)}")
        return {"files": result.get("files", []), "nextPageToken": result.get("nextPageToken")}

    def get_account(self) -> dict[str, str]:
        result = self._request(f"{DRIVE_API}/about?{urlencode({'fields': 'user(displayName,emailAddress)'})}")
        user = result.get("user") or {}
        return {"email": str(user.get("emailAddress") or ""), "name": str(user.get("displayName") or "")}

    def get_file_content(self, file_id: str) -> tuple[dict[str, Any], bytes, str]:
        metadata = self._request(
            f"{DRIVE_API}/files/{quote(file_id, safe='')}?{urlencode({'fields': 'id,name,mimeType,size'})}"
        )
        mime_type = str(metadata.get("mimeType") or "application/octet-stream")
        if mime_type.startswith("application/vnd.google-apps."):
            export_url = f"{DRIVE_API}/files/{quote(file_id, safe='')}/export?{urlencode({'mimeType': 'text/plain'})}"
            content, returned_type = self._request(export_url, binary=True)
            return metadata, content, returned_type
        content, returned_type = self._request(
            f"{DRIVE_API}/files/{quote(file_id, safe='')}?alt=media",
            binary=True,
        )
        return metadata, content, returned_type or mime_type
