import base64
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from datetime import datetime
from urllib.parse import urlencode, quote
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import auth_guard
from app.api.schemas.google_drive_oauth_schema import GoogleOAuthCompletionIn
from app.infrastructure.database.models.analysis_model import GoogleDriveOAuthConnection
from app.infrastructure.database.session import get_db
from app.infrastructure.google_drive_read_service import (
    DRIVE_READONLY_SCOPE,
    GoogleDriveIntegrationError,
    GoogleDriveReauthenticationRequired,
    GoogleDriveService,
    decrypt_refresh_token,
    encrypt_refresh_token,
)

router = APIRouter(prefix="/api/v1/integrations/google", tags=["Google Drive (read-only)"])
logger = logging.getLogger(__name__)


def _owner(payload: dict) -> tuple[str, str]:
    tenant_id, user_id = payload.get("tenant_id"), payload.get("sub")
    if not tenant_id or not user_id:
        raise HTTPException(401, "Sessão inválida.")
    return str(tenant_id), str(user_id)


def _require_lawyer(payload=Depends(auth_guard)):
    if payload.get("role") != "advogado":
        raise HTTPException(403, "A integração com Google Drive está disponível somente para usuários com perfil advogado.")
    return payload


def _oauth_config() -> tuple[str, str, str, str]:
    client_id = os.getenv("KEALEX_GOOGLE_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.getenv("KEALEX_GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("KEALEX_GOOGLE_OAUTH_REDIRECT_URI", "").strip()
    state_secret = os.getenv("KEALEX_SECRET_KEY") or os.getenv("KEALEX_JWT_SECRET")
    if not all((client_id, client_secret, redirect_uri, state_secret)):
        raise HTTPException(503, "A autenticação OAuth do Google Drive não está configurada no servidor.")
    return client_id, client_secret, redirect_uri, state_secret


def _encode_state(payload: dict, secret: str, purpose: str = "readonly") -> str:
    claims = {
        "tenant_id": str(payload["tenant_id"]),
        "user_id": str(payload["sub"]),
        "iat": int(time.time()),
        "nonce": uuid.uuid4().hex,
        "purpose": purpose,
    }
    body = base64.urlsafe_b64encode(json.dumps(claims, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def _decode_state(state: str, secret: str, purpose: str = "readonly") -> dict:
    try:
        body, signature = state.split(".", 1)
        expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        claims = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if claims.get("purpose", "readonly") != purpose or not claims.get("nonce") or abs(int(time.time()) - int(claims["iat"])) > 600:
            raise ValueError("expired state")
        return claims
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(400, "A autorização do Google expirou ou é inválida. Inicie novamente.") from exc


def _connection(db: Session, tenant_id: str, user_id: str) -> GoogleDriveOAuthConnection:
    connection = db.query(GoogleDriveOAuthConnection).filter_by(tenant_id=tenant_id, user_id=user_id).first()
    if not connection:
        raise HTTPException(409, detail={"code": "google_reauth_required", "message": "Conecte sua conta Google Drive para consultar arquivos."})
    return connection


def _drive_service(connection: GoogleDriveOAuthConnection) -> GoogleDriveService:
    try:
        return GoogleDriveService(decrypt_refresh_token(connection.encrypted_refresh_token))
    except GoogleDriveIntegrationError as exc:
        raise HTTPException(500, str(exc)) from exc


@router.get("/auth")
def google_auth(payload=Depends(_require_lawyer)):
    """Start OAuth for authenticated API clients that can follow HTTP redirects."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(_authorization_url(payload), status_code=302)


def _authorization_url(payload: dict) -> str:
    client_id, _, redirect_uri, secret = _oauth_config()
    state = _encode_state(payload, secret)
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": DRIVE_READONLY_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    })


@router.get("/upload/auth/url")
def google_upload_auth_url(payload=Depends(_require_lawyer)):
    client_id, _, redirect_uri, secret = _oauth_config()
    state = _encode_state(payload, secret, purpose="upload")
    return {"authorizationUrl": "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/drive.file",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    })}


@router.post("/upload/callback")
def complete_google_upload_oauth(body: GoogleOAuthCompletionIn, payload=Depends(_require_lawyer)):
    from google_auth_oauthlib.flow import Flow

    client_id, client_secret, redirect_uri, secret = _oauth_config()
    claims = _decode_state(body.state, secret, purpose="upload")
    tenant_id, user_id = _owner(payload)
    if (claims.get("tenant_id"), claims.get("user_id")) != (tenant_id, user_id):
        raise HTTPException(403, "Esta autoriza\u00e7\u00e3o foi iniciada por outra sess\u00e3o.")

    flow = Flow.from_client_config(
        {"web": {"client_id": client_id, "client_secret": client_secret, "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token"}},
        scopes=["https://www.googleapis.com/auth/drive.file"],
        redirect_uri=redirect_uri,
    )
    try:
        flow.fetch_token(code=body.code)
        credentials = flow.credentials
        if not credentials.refresh_token:
            raise HTTPException(400, "O Google n\u00e3o retornou refresh_token. Revogue o acesso anterior e autorize novamente.")
        return {
            "type": "authorized_user",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": credentials.refresh_token,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Google Drive upload OAuth exchange failed")
        raise HTTPException(502, "N\u00e3o foi poss\u00edvel gerar as credenciais do Google Drive.") from exc

@router.get("/auth/url")
def google_auth_url(payload=Depends(_require_lawyer)):
    """Return the Google URL for SPAs using bearer-token authentication."""
    return {"authorizationUrl": _authorization_url(payload)}


@router.get("/callback")
def google_callback(code: str = "", state: str = "", error: str = ""):
    """Relay Google's one-time authorization code to the authenticated SPA completion step."""
    app_url = os.getenv("KEALEX_PUBLIC_APP_URL", "").strip().rstrip("/")
    if not app_url:
        raise HTTPException(503, "Configure KEALEX_PUBLIC_APP_URL para concluir a autorização Google.")
    if error or not code or not state:
        params = {"google_drive_oauth_error": "1"}
    else:
        params = {"google_drive_oauth_code": code, "google_drive_oauth_state": state}
        try:
            _, _, _, secret = _oauth_config()
            _decode_state(state, secret, purpose="upload")
            params["google_drive_oauth_type"] = "upload"
        except HTTPException:
            pass
    return RedirectResponse(f"{app_url}/perfil?{urlencode(params)}", status_code=303)


@router.post("/callback")
def complete_google_callback(body: GoogleOAuthCompletionIn, db: Session = Depends(get_db), payload=Depends(_require_lawyer)):
    client_id, client_secret, redirect_uri, secret = _oauth_config()
    claims = _decode_state(body.state, secret)
    tenant_id, user_id = _owner(payload)
    if (claims.get("tenant_id"), claims.get("user_id")) != (tenant_id, user_id):
        raise HTTPException(403, "Esta autorização foi iniciada por outra sessão.")

    token_request = Request(
        "https://oauth2.googleapis.com/token",
        data=urlencode({
            "code": body.code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(token_request, timeout=20) as response:
            token_payload = json.loads(response.read().decode("utf-8"))
        refresh_token = token_payload.get("refresh_token")
        if not refresh_token:
            raise HTTPException(400, "O Google não retornou refresh_token. Tente autorizar novamente.")
        granted_scopes_value = token_payload.get("scope")
        granted_scopes = set(str(granted_scopes_value).split())
        if granted_scopes_value and DRIVE_READONLY_SCOPE not in granted_scopes:
            raise HTTPException(403, "A conta não concedeu a permissão de leitura do Google Drive.")

        service = GoogleDriveService(refresh_token, client_id=client_id, client_secret=client_secret)
        account = service.get_account()
        encrypted_token = encrypt_refresh_token(refresh_token)
        connection = db.query(GoogleDriveOAuthConnection).filter_by(tenant_id=tenant_id, user_id=user_id).first()
        if connection:
            connection.encrypted_refresh_token = encrypted_token
            connection.email = account.get("email") or None
            connection.scopes = DRIVE_READONLY_SCOPE
            connection.updated_at = datetime.utcnow()
        else:
            connection = GoogleDriveOAuthConnection(
                tenant_id=tenant_id,
                user_id=user_id,
                encrypted_refresh_token=encrypted_token,
                email=account.get("email") or None,
                scopes=DRIVE_READONLY_SCOPE,
            )
            db.add(connection)
        db.commit()
        return {"connected": True, "email": connection.email, "scope": connection.scopes}
    except HTTPException:
        db.rollback()
        raise
    except (HTTPError, URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError, SQLAlchemyError, GoogleDriveIntegrationError, ValueError) as exc:
        db.rollback()
        logger.exception("Google Drive OAuth exchange failed")
        if isinstance(exc, GoogleDriveReauthenticationRequired):
            raise HTTPException(400, "O Google recusou a autorização. Revise o consentimento e tente novamente.") from exc
        raise HTTPException(502, "Não foi possível concluir a conexão com o Google Drive.") from exc


@router.get("/connection")
def get_google_connection(db: Session = Depends(get_db), payload=Depends(_require_lawyer)):
    tenant_id, user_id = _owner(payload)
    connection = db.query(GoogleDriveOAuthConnection).filter_by(tenant_id=tenant_id, user_id=user_id).first()
    return {
        "connected": bool(connection),
        "email": connection.email if connection else None,
        "scope": connection.scopes if connection else None,
        "updatedAt": connection.updated_at.isoformat() if connection else None,
    }


@router.get("/files")
def list_google_drive_files(
    query: str | None = None,
    page_size: int = Query(default=50, ge=1, le=100),
    page_token: str | None = None,
    db: Session = Depends(get_db),
    payload=Depends(_require_lawyer),
):
    tenant_id, user_id = _owner(payload)
    service = _drive_service(_connection(db, tenant_id, user_id))
    try:
        return service.list_files(query=query, page_size=page_size, page_token=page_token)
    except GoogleDriveReauthenticationRequired as exc:
        raise HTTPException(409, detail={"code": "google_reauth_required", "message": str(exc)}) from exc
    except GoogleDriveIntegrationError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/files/{file_id}/content")
def get_google_drive_file_content(file_id: str, db: Session = Depends(get_db), payload=Depends(_require_lawyer)):
    tenant_id, user_id = _owner(payload)
    service = _drive_service(_connection(db, tenant_id, user_id))
    try:
        metadata, content, content_type = service.get_file_content(file_id)
        safe_name = quote(str(metadata.get("name") or "documento"))
        return Response(
            content=content,
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
        )
    except GoogleDriveReauthenticationRequired as exc:
        raise HTTPException(409, detail={"code": "google_reauth_required", "message": str(exc)}) from exc
    except GoogleDriveIntegrationError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.delete("/connection")
def disconnect_google_drive(db: Session = Depends(get_db), payload=Depends(_require_lawyer)):
    tenant_id, user_id = _owner(payload)
    connection = db.query(GoogleDriveOAuthConnection).filter_by(tenant_id=tenant_id, user_id=user_id).first()
    if connection:
        db.delete(connection)
        db.commit()
    return {"disconnected": True}
