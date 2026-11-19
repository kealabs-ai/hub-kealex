import base64
import hashlib
import hmac
import json
import logging
import os
import re
import uuid
from datetime import datetime, timedelta

from cryptography.fernet import Fernet
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.use_cases.certificates import validate_cnpj, validate_cpf
from app.core.config import FISCALAPI_RATE_LIMIT_PER_MINUTE, KEALEX_SECRET_KEY
from app.infrastructure.database.models import FiscalApiConsulta, FiscalApiDocumento
from app.infrastructure.fiscalapi_adapter import FiscalApiAdapter, FiscalApiError


logger = logging.getLogger(__name__)
PROVIDER = "fiscalapi"
SUPPORTED_UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}
FEDERAL_ENDPOINTS = {
    "cndt": ("/api/consultar-cndt", "CNDT / TST"),
    "crf_fgts": ("/api/consultar-crf-fgts", "CRF / FGTS / Caixa"),
    "cnd_federal": ("/api/consultar-cnd-federal", "CND Federal / RFB e PGFN"),
}
ENRICHMENT_ENDPOINTS = {
    "cnpj": "/api/consultar-cnpj",
    "simples_nacional": "/api/consultar-simples-nacional",
}
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
_storage_secret = os.getenv("CERTIFICATES_STORAGE_KEY") or KEALEX_SECRET_KEY
_document_cipher = Fernet(base64.urlsafe_b64encode(hashlib.sha256((_storage_secret + ":fiscalapi-documents:v1").encode()).digest()))


def _digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def _validate_uf(value: str) -> str:
    uf = (value or "").strip().upper()
    if uf not in SUPPORTED_UFS:
        raise HTTPException(422, "Informe uma UF válida entre as 27 unidades federativas.")
    return uf


def _document(payload: dict, allowed: tuple[str, ...], required: bool = True) -> tuple[str | None, str | None]:
    supplied = [name for name in allowed if payload.get(name) not in (None, "")]
    if len(supplied) > 1 or required and len(supplied) != 1:
        fields = ", ".join(allowed)
        raise HTTPException(422, f"Informe exatamente um identificador entre: {fields}.")
    if not supplied:
        return None, None

    name = supplied[0]
    value = str(payload[name]).strip()
    if name == "cpf":
        value = _digits(value)
        if not validate_cpf(value):
            raise HTTPException(422, "CPF inválido.")
    elif name == "cnpj":
        value = _digits(value)
        if not validate_cnpj(value):
            raise HTTPException(422, "CNPJ inválido.")
    elif name == "ie":
        value = re.sub(r"\s+", "", value)
        if not value or len(value) > 30 or not re.fullmatch(r"[A-Za-z0-9./-]+", value):
            raise HTTPException(422, "Inscrição Estadual inválida.")
    return name, value


def _document_prefer_cnpj(payload: dict) -> tuple[str, str]:
    return _document(payload, ("cpf", "cnpj"))


def build_provider_call(service: str, payload: dict) -> tuple[str, dict, str | None, str | None]:
    """Valida cada modalidade e produz somente parâmetros documentados pela FiscalAPI."""
    if service == "consulta-ie":
        identifier_type, identifier = _document(payload, ("cpf", "cnpj", "ie"))
        params = {"uf": _validate_uf(payload.get("uf")), identifier_type: identifier}
        if payload.get("secundarias") is True:
            params["secundarias"] = True
        return "/api/consultar", params, identifier_type, identifier

    if service == "enriquecimento":
        mode = payload.get("tipo")
        endpoint = ENRICHMENT_ENDPOINTS.get(mode)
        if not endpoint:
            raise HTTPException(422, "Tipo de enriquecimento não suportado. Use cnpj ou simples_nacional.")
        cnpj_value = str(payload.get("cnpj") or "").strip()
        compact_cnpj = re.sub(r"[^A-Za-z0-9]", "", cnpj_value).upper()
        if mode == "simples_nacional" and len(compact_cnpj) == 14 and compact_cnpj.isalnum() and not compact_cnpj.isdigit():
            cnpj_value = compact_cnpj
        else:
            _, cnpj_value = _document({"cnpj": cnpj_value}, ("cnpj",))
        params = {"cnpj": cnpj_value}
        if mode == "cnpj" and payload.get("force_fresh") is True:
            params["force_fresh"] = True
        return endpoint, params, "cnpj", cnpj_value

    if service == "cnd-estadual":
        identifier_type, identifier = _document(payload, ("cpf", "cnpj"))
        return "/api/consultar-cnd", {"uf": _validate_uf(payload.get("uf")), identifier_type: identifier}, identifier_type, identifier

    if service == "federais":
        certificate_type = payload.get("tipo")
        endpoint_and_name = FEDERAL_ENDPOINTS.get(certificate_type)
        if not endpoint_and_name:
            raise HTTPException(422, "Tipo de certidão federal não suportado.")
        endpoint, _ = endpoint_and_name
        identifier_type, identifier = _document_prefer_cnpj(payload)
        if certificate_type == "cnd_federal" and identifier_type != "cnpj":
            raise HTTPException(422, "A CND Federal da FiscalAPI aceita somente CNPJ.")
        params = {identifier_type: identifier}
        if certificate_type == "cnd_federal" and payload.get("emitir_nova") is True:
            params["emitir_nova"] = True
        return endpoint, params, identifier_type, identifier

    if service == "sigef":
        identifier_type, identifier = _document(payload, ("cpf", "cnpj"))
        return "/api/consultar-sigef", {identifier_type: identifier}, identifier_type, identifier

    raise HTTPException(404, "Serviço FiscalAPI não encontrado.")


def _mask(value: str | None) -> str | None:
    if not value:
        return None
    digits = _digits(value)
    if len(digits) == 11:
        return f"***.***.{digits[6:9]}-**"
    if len(digits) == 14:
        return f"**.***.***/{digits[8:12]}-**"
    return f"••••{value[-4:]}"


def _extract_pdf(value):
    if isinstance(value, dict):
        for key, nested in value.items():
            if key.lower() == "pdf_base64" and isinstance(nested, str) and nested:
                return nested
            found = _extract_pdf(nested)
            if found:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _extract_pdf(nested)
            if found:
                return found
    return None


def _without_pdf(value):
    if isinstance(value, dict):
        return {key: _without_pdf(item) for key, item in value.items() if key.lower() != "pdf_base64"}
    if isinstance(value, list):
        return [_without_pdf(item) for item in value]
    return value


def _normalized_data(service: str, payload: dict, body: dict) -> dict:
    if service == "consulta-ie":
        return {
            "uf": body.get("uf", payload.get("uf")),
            "results": body.get("results") if isinstance(body.get("results"), list) else [],
            "cached": body.get("cached"),
            "dataAtualizacao": body.get("data_atualizacao"),
        }
    if service == "enriquecimento" and payload.get("tipo") == "simples_nacional":
        return body.get("result") if isinstance(body.get("result"), dict) else body
    return body.get("result") if isinstance(body.get("result"), (dict, list)) else body


def _source_failed(body: dict, data) -> bool:
    if str(body.get("status", "")).lower() in {"error", "erro"}:
        return True
    source = body.get("source_status")
    if isinstance(source, dict) and str(source.get("status", "")).lower() in {"error", "erro", "indisponivel"}:
        return True
    if isinstance(data, dict) and str(data.get("status", "")).lower() in {"error", "erro"}:
        return True
    return False


def _no_results(service: str, data) -> bool:
    if service == "consulta-ie":
        return not data.get("results")
    if service == "sigef" and isinstance(data, dict):
        parcelas = data.get("parcelas")
        return data.get("total_parcelas") == 0 or isinstance(parcelas, list) and not parcelas
    return False


def _response(row: FiscalApiConsulta) -> dict:
    data = _decrypt_json(row.normalized_result_json) if row.normalized_result_json else None
    success = row.status in {"CONCLUIDA", "SEM_RESULTADOS"}
    error = None if success else {"code": row.error_code or row.status, "message": row.public_error or "A consulta não pôde ser concluída."}
    return {
        "success": success,
        "data": data,
        "metadata": {
            "provider": PROVIDER,
            "service": row.service,
            "request_id": row.id,
            "provider_request_id": row.provider_request_id,
            "consulted_at": row.completed_at.isoformat() if row.completed_at else row.created_at.isoformat() if row.created_at else None,
            "status": row.status,
            "document_available": _document_exists(row),
            "operational_cost_cents": row.operational_cost_cents,
        },
        "error": error,
    }


def _document_exists(row: FiscalApiConsulta) -> bool:
    return getattr(row, "document_available", False)


def _encrypt_json(value) -> str:
    serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str).encode()
    return _document_cipher.encrypt(serialized).decode()


def _decrypt_json(value: str):
    return json.loads(_document_cipher.decrypt(value.encode()))


def _raise_stored_error(row: FiscalApiConsulta) -> None:
    if row.status == "PROCESSANDO":
        raise HTTPException(409, {"code": "CONSULTA_EM_PROCESSAMENTO", "message": "A solicitação com esta chave ainda está sendo processada.", "request_id": row.id})
    if row.http_error_code:
        headers = {"Retry-After": row.retry_after} if getattr(row, "retry_after", None) else None
        raise HTTPException(row.http_error_code, {"code": row.error_code, "message": row.public_error}, headers=headers)


def _safe_status(service: str, body: dict, data) -> str:
    if _source_failed(body, data):
        return "FALHA_FONTE"
    if _no_results(service, data):
        return "SEM_RESULTADOS"
    return "CONCLUIDA"


def create_consultation(
    db: Session,
    tenant_id: str,
    user_id: str,
    service: str,
    payload: dict,
    idempotency_key: str,
    adapter: FiscalApiAdapter | None = None,
) -> dict:
    key = (idempotency_key or "").strip()
    if not key or len(key) > 120:
        raise HTTPException(422, "Informe uma chave Idempotency-Key válida de até 120 caracteres.")
    path, params, identifier_type, identifier = build_provider_call(service, payload)
    canonical = json.dumps({"service": service, "path": path, "params": params}, sort_keys=True, separators=(",", ":"))
    request_hash = hashlib.sha256(canonical.encode()).hexdigest()

    existing = db.query(FiscalApiConsulta).filter_by(tenant_id=tenant_id, user_id=user_id, idempotency_key=key).first()
    if existing:
        if not hmac.compare_digest(existing.request_hash, request_hash):
            raise HTTPException(409, "A chave Idempotency-Key já foi usada com parâmetros diferentes.")
        _raise_stored_error(existing)
        existing.document_available = db.query(FiscalApiDocumento.id).filter_by(consultation_id=existing.id).first() is not None
        return _response(existing)

    if FISCALAPI_RATE_LIMIT_PER_MINUTE > 0:
        window_start = datetime.utcnow() - timedelta(minutes=1)
        recent_requests = db.query(func.count(FiscalApiConsulta.id)).filter(
            FiscalApiConsulta.tenant_id == tenant_id,
            FiscalApiConsulta.created_at >= window_start,
        ).scalar() or 0
        if recent_requests >= FISCALAPI_RATE_LIMIT_PER_MINUTE:
            raise HTTPException(429, "Limite de consultas do escrit?rio atingido. Aguarde antes de tentar novamente.")

    identifier_hash = hmac.new(KEALEX_SECRET_KEY.encode(), identifier.encode(), hashlib.sha256).hexdigest() if identifier else None
    row = FiscalApiConsulta(
        id=str(uuid.uuid4()), tenant_id=tenant_id, user_id=user_id, service=service,
        provider=PROVIDER, idempotency_key=key, request_hash=request_hash,
        subject_type=identifier_type, subject_masked=_mask(identifier), subject_hash=identifier_hash,
        status="PROCESSANDO", created_at=datetime.utcnow(),
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        raced = db.query(FiscalApiConsulta).filter_by(tenant_id=tenant_id, user_id=user_id, idempotency_key=key).first()
        if raced:
            if not hmac.compare_digest(raced.request_hash, request_hash):
                raise HTTPException(409, "A chave Idempotency-Key já foi usada com parâmetros diferentes.")
            _raise_stored_error(raced)
            raced.document_available = db.query(FiscalApiDocumento.id).filter_by(consultation_id=raced.id).first() is not None
            return _response(raced)
        raise

    client = adapter or FiscalApiAdapter()
    try:
        body = client.get(path, params)
    except FiscalApiError as exc:
        row.status = "FALHA"
        row.error_code = exc.code
        row.public_error = exc.message[:240]
        row.http_error_code = exc.status_code
        row.retry_after = exc.retry_after
        row.completed_at = datetime.utcnow()
        db.commit()
        logger.warning("FiscalAPI consultation failed: service=%s request_id=%s status=%s code=%s", service, row.id, exc.status_code, exc.code)
        headers = {"Retry-After": exc.retry_after} if exc.retry_after else None
        raise HTTPException(exc.status_code, {"code": exc.code, "message": exc.message, "request_id": row.id}, headers=headers) from exc
    except Exception as exc:
        row.status = "FALHA"
        row.error_code = "ERRO_INTERNO"
        row.public_error = "Não foi possível concluir a consulta agora. Tente novamente mais tarde."
        row.http_error_code = 502
        row.completed_at = datetime.utcnow()
        db.commit()
        logger.exception("Unexpected FiscalAPI integration error: service=%s request_id=%s", service, row.id)
        raise HTTPException(502, {"code": row.error_code, "message": row.public_error, "request_id": row.id}) from exc

    data = _normalized_data(service, payload, body)
    sanitized_body = _without_pdf(body)
    row.provider_request_id = str(body.get("request_id") or "")[:100] or None
    row.normalized_result_json = _encrypt_json(_without_pdf(data))
    row.provider_response_json = _encrypt_json(sanitized_body)
    row.status = _safe_status(service, body, data)
    row.completed_at = datetime.utcnow()

    encoded_pdf = _extract_pdf(body)
    document_available = False
    if encoded_pdf:
        try:
            encoded_pdf = encoded_pdf.split(",", 1)[1] if encoded_pdf.startswith("data:application/pdf;base64,") else encoded_pdf
            content = base64.b64decode(encoded_pdf, validate=True)
        except (ValueError, TypeError):
            content = b""
        if content.startswith(b"%PDF-") and len(content) <= MAX_DOCUMENT_BYTES:
            document = FiscalApiDocumento(
                id=str(uuid.uuid4()), consultation_id=row.id,
                file_hash=hashlib.sha256(content).hexdigest(),
                filename=f"{service}-{row.id}.pdf", file_data=_document_cipher.encrypt(content),
                size_bytes=len(content), created_at=datetime.utcnow(),
            )
            db.add(document)
            document_available = True
    row.document_available = document_available
    db.commit()
    db.refresh(row)
    return _response(row)


def get_consultation(db: Session, tenant_id: str, user_id: str, consultation_id: str) -> dict:
    row = db.query(FiscalApiConsulta).filter_by(id=consultation_id, tenant_id=tenant_id, user_id=user_id).first()
    if not row:
        raise HTTPException(404, "Consulta não encontrada.")
    row.document_available = db.query(FiscalApiDocumento.id).filter_by(consultation_id=row.id).first() is not None
    return _response(row)


def get_consultation_document(db: Session, tenant_id: str, user_id: str, consultation_id: str) -> tuple[bytes, str]:
    row = db.query(FiscalApiConsulta).filter_by(id=consultation_id, tenant_id=tenant_id, user_id=user_id).first()
    if not row:
        raise HTTPException(404, "Consulta não encontrada.")
    document = db.query(FiscalApiDocumento).filter_by(consultation_id=row.id).first()
    if not document:
        raise HTTPException(404, "O fornecedor não disponibilizou PDF para esta consulta.")
    try:
        content = _document_cipher.decrypt(document.file_data)
    except Exception as exc:
        raise HTTPException(500, "Não foi possível validar o documento armazenado.") from exc
    if not hmac.compare_digest(hashlib.sha256(content).hexdigest(), document.file_hash):
        raise HTTPException(500, "A integridade do documento armazenado não pôde ser confirmada.")
    return content, document.filename
