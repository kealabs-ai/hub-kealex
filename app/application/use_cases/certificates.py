import base64
import hashlib
import hmac
import json
import os
import re
import threading
import time
import uuid
from datetime import date, datetime, time as datetime_time

import httpx
from cryptography.fernet import Fernet
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import KEALEX_SECRET_KEY
from app.infrastructure.database.models import CertificateAuditLog, CertificateDocument, CertificateRequest
from app.application.use_cases.kea_credits import confirm_service_credits, refund_service_credits, reserve_service_credits


PROVIDERS = {
    "receita-federal": {"name": "Receita Federal / PGFN", "type": "Certidão de Regularidade Fiscal", "portal": "https://www.gov.br/pt-br/servicos/emitir-certidao-de-regularidade-fiscal-perante-a-fazenda-nacional"},
    "policia-federal": {"name": "Polícia Federal", "type": "Antecedentes Criminais", "portal": "https://www.gov.br/pf/pt-br/assuntos/antecedentes-criminais"},
    "sefaz": {"name": "SEFAZ", "type": "Certidão de Débitos Estaduais", "portal": "https://www.fazenda.mg.gov.br/empresas/certidao_debitos/"},
    "tst": {"name": "TST", "type": "Certidão Negativa de Débitos Trabalhistas", "portal": "https://cndt-certidao.tst.jus.br/"},
    "cgu": {"name": "CGU", "type": "Certidões Correcionais e de Sanções", "portal": "https://certidoes.cgu.gov.br/"},
    "onr": {"name": "ONR", "type": "Certidão de Registro de Imóveis", "portal": "https://www.ridigital.org.br/"},
}

_storage_secret = os.getenv("CERTIFICATES_STORAGE_KEY") or KEALEX_SECRET_KEY
_document_cipher = Fernet(base64.urlsafe_b64encode(hashlib.sha256((_storage_secret + ":certificate-documents:v1").encode()).digest()))

API_FLAGS = {
    "receita-federal": "RECEITA_API_ENABLED",
    "policia-federal": "PF_API_ENABLED",
    "sefaz": "SEFAZ_API_ENABLED",
    "tst": "TST_API_ENABLED",
    "cgu": "CGU_API_ENABLED",
    "onr": "ONR_API_ENABLED",
}

REQUIREMENTS = {
    "receita-federal": [{"name": "document", "label": "CPF ou CNPJ", "type": "cpf_cnpj", "required": True}],
    "policia-federal": [{"name": "nome", "label": "Nome completo", "type": "text", "required": True}, {"name": "document", "label": "CPF", "type": "cpf", "required": True}, {"name": "data_nascimento", "label": "Data de nascimento", "type": "date", "required": True}, {"name": "nome_mae", "label": "Nome da mãe", "type": "text", "required": False}],
    "sefaz": [{"name": "document", "label": "CPF ou CNPJ", "type": "cpf_cnpj", "required": True}, {"name": "uf", "label": "UF (integração preparada para MG)", "type": "uf", "required": True, "options": ["MG"]}],
    "tst": [{"name": "document", "label": "CPF ou CNPJ", "type": "cpf_cnpj", "required": True}],
    "cgu": [{"name": "document", "label": "CPF ou CNPJ", "type": "cpf_cnpj", "required": True}],
    "onr": [{"name": "uf", "label": "UF do imóvel", "type": "uf", "required": True}, {"name": "matricula", "label": "Matrícula do imóvel", "type": "text", "required": True}, {"name": "cartorio", "label": "Cartório ou serventia", "type": "text", "required": False}],
}

_TOKEN_CACHE = {"token": None, "expires_at": 0.0}
_TOKEN_LOCK = threading.Lock()
_CND_TIMEOUT = httpx.Timeout(20.0, connect=5.0)


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def validate_cpf(value: str) -> bool:
    value = _digits(value)
    if len(value) != 11 or len(set(value)) == 1:
        return False
    digits = [int(char) for char in value]
    for position in (9, 10):
        weight = position + 1
        total = sum(digits[index] * (weight - index) for index in range(position))
        check = (total * 10 % 11) % 10
        if digits[position] != check:
            return False
    return True


def validate_cnpj(value: str) -> bool:
    value = _digits(value)
    if len(value) != 14 or len(set(value)) == 1:
        return False
    digits = [int(char) for char in value]
    for position, weights in ((12, (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)), (13, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))):
        remainder = sum(digits[index] * weights[index] for index in range(position)) % 11
        check = 0 if remainder < 2 else 11 - remainder
        if digits[position] != check:
            return False
    return True


def _conecta_configured() -> bool:
    enabled = os.getenv(API_FLAGS["receita-federal"], "false").lower() in {"1", "true", "yes", "on"}
    return enabled and all(os.getenv(name, "").strip() for name in ("CONECTA_CND_ACCESS_KEY", "CONECTA_CND_ACCESS_SECRET", "CONECTA_CND_TOKEN_URL", "CONECTA_CND_ENDPOINT"))


def _mode(provider: str) -> str:
    if os.getenv("CERTIFICATES_ENABLED", "true").lower() not in {"1", "true", "yes", "on"}:
        return "UNAVAILABLE"
    if provider == "receita-federal" and _conecta_configured():
        return "OFFICIAL_API"
    return "OFFICIAL_PORTAL"


def provider_catalog():
    result = []
    for key, provider in PROVIDERS.items():
        mode = _mode(key)
        api_available = key == "receita-federal" and mode == "OFFICIAL_API"
        result.append({"id": key, **provider, "integrationMode": mode, "apiAvailable": api_available, "portalAvailable": mode in {"OFFICIAL_PORTAL", "OFFICIAL_API"}, "portalUrl": provider["portal"]})
    return result


def requirements_for(provider: str):
    if provider not in PROVIDERS:
        raise HTTPException(404, "Emissor não encontrado")
    return {"provider": provider, "fields": REQUIREMENTS[provider], "integrationMode": _mode(provider)}


def availability_for(provider: str):
    config = next((item for item in provider_catalog() if item["id"] == provider), None)
    if not config:
        raise HTTPException(404, "Emissor não encontrado")
    if config["integrationMode"] == "UNAVAILABLE":
        message = "O módulo de certidões está desabilitado."
    elif config["apiAvailable"]:
        message = "A emissão será feita pela API CND oficial da Receita Federal e PGFN. A consulta exige credenciais Conecta liberadas e pode gerar cobrança conforme o contrato Serpro."
    else:
        message = "A emissão automatizada não está configurada. Acesse o portal oficial e anexe o PDF obtido para mantê-lo neste histórico."
    return {"provider": provider, "available": config["integrationMode"] != "UNAVAILABLE", "integrationMode": config["integrationMode"], "apiAvailable": config["apiAvailable"], "message": message, "portalUrl": config["portalUrl"]}


def _validate_request(provider: str, fields: dict):
    requirements = REQUIREMENTS[provider]
    allowed_fields = {field["name"] for field in requirements}
    if set(fields) - allowed_fields:
        raise HTTPException(422, "A solicitação contém campos não aceitos para este emissor")
    if any(len(value) > 250 for value in fields.values()):
        raise HTTPException(422, "Um ou mais campos excedem o tamanho permitido")
    for field in requirements:
        value = fields.get(field["name"])
        if field["required"] and (not isinstance(value, str) or not value.strip()):
            raise HTTPException(422, f"O campo {field['label']} é obrigatório")
    document = _digits(fields.get("document", ""))
    if document:
        valid = validate_cpf(document) if len(document) == 11 else validate_cnpj(document) if len(document) == 14 else False
        if not valid:
            raise HTTPException(422, "CPF ou CNPJ inválido")
    uf = fields.get("uf")
    if uf and not re.fullmatch(r"(?i)(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)", uf.strip()):
        raise HTTPException(422, "UF inválida")
    if provider == "sefaz" and uf and uf.strip().upper() != "MG":
        raise HTTPException(422, "A integração SEFAZ preparada nesta versão é para Minas Gerais (MG)")


def _mask(value: str) -> str:
    value = _digits(value)
    if len(value) == 11:
        return f"***.***.{value[6:9]}-**"
    if len(value) == 14:
        return f"**.***.***/{value[8:12]}-**"
    return f"••••{value[-4:]}" if value else "Identificador do imóvel"


def _audit(db: Session, request: CertificateRequest, user_id: str, action: str):
    db.add(CertificateAuditLog(request_id=request.id, tenant_id=request.tenant_id, user_id=user_id, action=action, status=request.status))


def _conecta_urls():
    token_url = os.getenv("CONECTA_CND_TOKEN_URL", "").strip()
    endpoint = os.getenv("CONECTA_CND_ENDPOINT", "").strip()
    if not token_url or not endpoint:
        raise RuntimeError("Configure os endpoints oficiais de token e CND do ambiente autorizado.")
    if not token_url.startswith("https://") or not endpoint.startswith("https://"):
        raise RuntimeError("Os endpoints do Conecta devem usar HTTPS.")
    return token_url, endpoint


def _conecta_token(client: httpx.Client, force_refresh: bool = False) -> str:
    with _TOKEN_LOCK:
        if not force_refresh and _TOKEN_CACHE["token"] and _TOKEN_CACHE["expires_at"] > time.monotonic() + 60:
            return _TOKEN_CACHE["token"]
        token_url, _ = _conecta_urls()
        try:
            response = client.post(
                token_url,
                auth=(os.environ["CONECTA_CND_ACCESS_KEY"], os.environ["CONECTA_CND_ACCESS_SECRET"]),
                data={"grant_type": "client_credentials"},
                headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise RuntimeError("Não foi possível autenticar no Conecta gov.br.") from exc
        token = body.get("access_token") or body.get("accessToken") or body.get("token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("O serviço de autenticação do Conecta não retornou um token válido.")
        expires_in = body.get("expires_in", 7200)
        try:
            lifetime = max(60, int(expires_in))
        except (TypeError, ValueError):
            lifetime = 7200
        _TOKEN_CACHE.update(token=token, expires_at=time.monotonic() + lifetime)
        return token


def _conecta_post(client: httpx.Client, body: dict) -> tuple[dict, int]:
    _, endpoint = _conecta_urls()
    token = _conecta_token(client)
    for attempt in range(2):
        try:
            response = client.post(endpoint, json=body, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        except httpx.HTTPError as exc:
            raise RuntimeError("Não foi possível conectar à API CND da Receita Federal.") from exc
        if response.status_code == 401 and attempt == 0:
            token = _conecta_token(client, force_refresh=True)
            continue
        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError("A API CND retornou uma resposta inválida.") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("A API CND retornou uma resposta inválida.")
        if response.status_code >= 500 and not payload.get("Status"):
            raise RuntimeError("A API CND está temporariamente indisponível.")
        return payload, response.status_code
    raise RuntimeError("Não foi possível autenticar a consulta na API CND.")


def _consultar_cnd(identifier: str, key: str | None = None) -> dict:
    pessoa_juridica = len(identifier) == 14
    request_body = {
        "TipoContribuinte": 1 if pessoa_juridica else 2,
        "ContribuinteConsulta": identifier,
        "CodigoIdentificacao": "9201" if pessoa_juridica else "9202",
        "GerarCertidaoPdf": True,
    }
    if key:
        request_body["Chave"] = key
    try:
        with httpx.Client(timeout=_CND_TIMEOUT) as client:
            for attempt in range(4):
                response, http_status = _conecta_post(client, request_body)
                status = response.get("Status")
                if status in {5, 6} and attempt < 3:
                    time.sleep(0.6)
                    continue
                if http_status >= 400 and status is None:
                    raise RuntimeError("A API CND recusou a solicitação. Verifique credenciais, ambiente e permissão de IP.")
                return response
    except httpx.HTTPError as exc:
        raise RuntimeError("Não foi possível concluir a consulta à Receita Federal.") from exc
    raise RuntimeError("A API CND não concluiu a consulta.")

def _parse_date(value: str | None, include_time: bool = False):
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        try:
            parsed_date = date.fromisoformat(value)
            return datetime.combine(parsed_date, datetime_time.min)
        except ValueError:
            return None


def _save_official_document(db: Session, row: CertificateRequest, certificate: dict) -> bool:
    encoded_pdf = certificate.get("DocumentoPdf")
    if not isinstance(encoded_pdf, str) or not encoded_pdf:
        return False
    try:
        content = base64.b64decode(re.sub(r"\s+", "", encoded_pdf), validate=True)
    except (ValueError, base64.binascii.Error):
        return False
    if not content.startswith(b"%PDF-") or len(content) > 10 * 1024 * 1024:
        return False
    document = db.query(CertificateDocument).filter_by(request_id=row.id).first() or CertificateDocument(request_id=row.id)
    document.file_hash = hashlib.sha256(content).hexdigest()
    document.content_type = "application/pdf"
    document.filename = f"certidao-receita-federal-{row.id[:8]}.pdf"
    document.file_data = _document_cipher.encrypt(content)
    document.upload_source = "receita_federal_api"
    document.validation_status = "validated_official"
    document.certificate_number = str(certificate.get("CodigoControle") or "")[:120] or None
    document.issued_at = _parse_date(certificate.get("DataEmissao"), include_time=True)
    document.expires_at = _parse_date(certificate.get("DataValidade"))
    db.add(document)
    row.document = document
    return True


def _apply_cnd_result(db: Session, row: CertificateRequest, response: dict, user_id: str):
    status = response.get("Status")
    api_message = response.get("Mensagem")
    certificate = response.get("Certidao")
    if status in {1, 2} and isinstance(certificate, dict):
        pdf_saved = _save_official_document(db, row, certificate)
        row.status = "ISSUED"
        row.completed_at = datetime.utcnow()
        row.external_protocol = str(certificate.get("CodigoControle") or row.id)[:120]
        row.error_code = None if pdf_saved else "PDF_OFICIAL_INDISPONIVEL"
        row.result_message = "Certidão emitida ou localizada pela API oficial; PDF armazenado." if pdf_saved else "Certidão emitida ou localizada, mas a API não retornou um PDF válido."
        _audit(db, row, user_id, "official_certificate_issued")
    elif status in {3, 4}:
        row.status = "NOT_ISSUED"
        row.completed_at = datetime.utcnow()
        row.error_code = f"CONECTA_STATUS_{status}"
        row.result_message = str(api_message or "A Receita Federal não emitiu a certidão.")[:250]
        _audit(db, row, user_id, "official_certificate_not_issued")
    elif status == 7:
        row.status = "PROCESSING"
        row.error_code = "CONECTA_PROCESSING"
        row.result_message = str(api_message or "A consulta continua em processamento.")[:250]
        row.result_key = str(response.get("Chave") or "") or None
        _audit(db, row, user_id, "official_certificate_processing")
    elif status in {5, 6}:
        row.status = "FAILED"
        row.error_code = f"CONECTA_STATUS_{status}"
        row.result_message = str(api_message or "O serviço da Receita Federal está temporariamente indisponível. Tente novamente.")[:250]
        _audit(db, row, user_id, "official_certificate_temporarily_unavailable")
    else:
        row.status = "FAILED"
        row.error_code = f"CONECTA_STATUS_{status}" if status is not None else "CONECTA_INVALID_RESPONSE"
        row.result_message = str(api_message or "A API CND não concluiu a emissão da certidão.")[:250]
        _audit(db, row, user_id, "official_certificate_failed")
    row.updated_at = datetime.utcnow()
    confirm_service_credits(db, row.tenant_id, f"certidao:{row.id}")
    db.commit()
    db.refresh(row)
    return serialize_request(row)


def create_request(db: Session, payload: dict, provider: str, fields: dict):
    if provider not in PROVIDERS:
        raise HTTPException(404, "Emissor não encontrado")
    mode = _mode(provider)
    if mode == "UNAVAILABLE":
        raise HTTPException(503, "Módulo de certidões desabilitado")
    _validate_request(provider, fields)
    identifier = _digits(fields.get("document", "")) or str(fields.get("matricula", "")).strip()
    row = CertificateRequest(
        id=str(uuid.uuid4()), tenant_id=str(payload["tenant_id"]), user_id=str(payload["sub"]),
        provider=provider, certificate_type=PROVIDERS[provider]["type"],
        subject_type="CPF" if len(identifier) == 11 else "CNPJ" if len(identifier) == 14 else "IMOVEL",
        subject_identifier_masked=_mask(identifier), subject_identifier_hash=hmac.new(_storage_secret.encode(), identifier.encode(), hashlib.sha256).hexdigest(),
        request_payload="{}", status="PENDING" if mode == "OFFICIAL_API" else "MANUAL_ACTION_REQUIRED", portal_url=PROVIDERS[provider]["portal"],
    )
    db.add(row)
    _audit(db, row, str(payload["sub"]), "request_created")
    if mode == "OFFICIAL_API":
        reserve_service_credits(db, row.tenant_id, row.user_id, "receita-federal", f"certidao:{row.id}")
    db.commit()
    db.refresh(row)
    if mode != "OFFICIAL_API":
        row.result_message = "Solicitação registrada. Abra o portal oficial para concluir a emissão."
        return serialize_request(row)
    try:
        response = _consultar_cnd(identifier)
    except RuntimeError as exc:
        refund_service_credits(db, row.tenant_id, row.user_id, f"certidao:{row.id}")
        row.status = "FAILED"
        row.error_code = "CONECTA_INDISPONIVEL"
        row.result_message = str(exc)
        row.updated_at = datetime.utcnow()
        _audit(db, row, str(payload["sub"]), "official_certificate_failed")
        db.commit()
        db.refresh(row)
        return serialize_request(row)
    return _apply_cnd_result(db, row, response, str(payload["sub"]))


def continue_cnd_request(db: Session, row: CertificateRequest, user_id: str, fields: dict, key: str):
    if row.provider != "receita-federal" or row.status != "PROCESSING":
        return serialize_request(row)
    if not _conecta_configured():
        raise HTTPException(503, "A integração Conecta da Receita Federal não está configurada.")
    _validate_request(row.provider, fields)
    identifier = _digits(fields.get("document", ""))
    provided_hash = hmac.new(_storage_secret.encode(), identifier.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(provided_hash, row.subject_identifier_hash):
        raise HTTPException(422, "O identificador não corresponde à solicitação em processamento.")
    try:
        response = _consultar_cnd(identifier, key=key)
    except RuntimeError as exc:
        row.status = "FAILED"
        row.error_code = "CONECTA_INDISPONIVEL"
        row.result_message = str(exc)
        row.updated_at = datetime.utcnow()
        _audit(db, row, user_id, "official_certificate_failed")
        db.commit()
        db.refresh(row)
        return serialize_request(row)
    return _apply_cnd_result(db, row, response, user_id)

def serialize_request(row: CertificateRequest):
    document = getattr(row, "document", None)
    return {"id": row.id, "protocol": row.external_protocol or row.id, "provider": row.provider, "certificateType": row.certificate_type, "subjectType": row.subject_type, "subjectIdentifierMasked": row.subject_identifier_masked, "status": row.status, "portalUrl": row.portal_url, "createdAt": row.created_at.isoformat() if row.created_at else None, "updatedAt": row.updated_at.isoformat() if row.updated_at else None, "completedAt": row.completed_at.isoformat() if row.completed_at else None, "documentAvailable": bool(document), "documentSource": document.upload_source if document else None, "validationStatus": document.validation_status if document else None, "expiresAt": document.expires_at.isoformat() if document and document.expires_at else None, "message": getattr(row, "result_message", None), "consultaKey": getattr(row, "result_key", None)}


def list_requests(db: Session, tenant_id: str, user_id: str, provider: str | None, status: str | None, page: int, page_size: int, sort_by: str = "created_at", sort_order: str = "desc"):
    query = db.query(CertificateRequest).filter_by(tenant_id=tenant_id, user_id=user_id)
    if provider:
        query = query.filter_by(provider=provider)
    if status:
        query = query.filter_by(status=status)
    total = query.count()
    sort_column = getattr(CertificateRequest, sort_by)
    ordering = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    rows = query.order_by(ordering).offset((page - 1) * page_size).limit(page_size).all()
    for row in rows:
        row.document = db.query(CertificateDocument).filter_by(request_id=row.id).first()
    return {"items": [serialize_request(row) for row in rows], "page": page, "pageSize": page_size, "total": total}


def get_owned_request(db: Session, tenant_id: str, user_id: str, request_id: str):
    row = db.query(CertificateRequest).filter_by(id=request_id, tenant_id=tenant_id, user_id=user_id).first()
    if not row:
        raise HTTPException(404, "Solicitação não encontrada")
    row.document = db.query(CertificateDocument).filter_by(request_id=row.id).first()
    return row


def upload_document(db: Session, row: CertificateRequest, user_id: str, filename: str, content: bytes):
    if not content.startswith(b"%PDF-") or len(content) > 10 * 1024 * 1024:
        raise HTTPException(422, "Envie um PDF válido de até 10 MB")
    existing = db.query(CertificateDocument).filter_by(request_id=row.id).first()
    document = existing or CertificateDocument(request_id=row.id)
    document.file_hash = hashlib.sha256(content).hexdigest()
    document.content_type = "application/pdf"
    document.filename = re.sub(r"[^A-Za-z0-9._-]", "_", filename or "certidao.pdf")[:180] or "certidao.pdf"
    document.file_data = _document_cipher.encrypt(content)
    document.upload_source = "user_upload"
    document.validation_status = "unverified"
    db.add(document)
    row.status = "MANUAL_ACTION_REQUIRED"
    row.updated_at = datetime.utcnow()
    _audit(db, row, user_id, "user_pdf_uploaded")
    db.commit()
    return document


def document_content(document: CertificateDocument) -> bytes:
    content = _document_cipher.decrypt(document.file_data)
    digest = hashlib.sha256(content).hexdigest()
    if not hmac.compare_digest(digest, document.file_hash):
        raise HTTPException(500, "A integridade do PDF armazenado não pôde ser confirmada")
    return content
