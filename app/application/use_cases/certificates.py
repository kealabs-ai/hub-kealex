import hashlib
import base64
import hmac
import os
import re
import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
from app.core.config import KEALEX_SECRET_KEY

from app.infrastructure.database.models import CertificateAuditLog, CertificateDocument, CertificateRequest


PROVIDERS = {
    "receita-federal": {"name": "Receita Federal / PGFN", "type": "Certidão de Débitos Federais", "portal": "https://www.gov.br/pt-br/servicos/emitir-certidao-de-regularidade-fiscal"},
    "policia-federal": {"name": "Polícia Federal", "type": "Antecedentes Criminais", "portal": "https://www.gov.br/pf/pt-br/assuntos/antecedentes-criminais"},
    "sefaz": {"name": "SEFAZ", "type": "Certidão de Débitos Estaduais", "portal": "https://www.fazenda.mg.gov.br/empresas/certidao_debitos/"},
    "tst": {"name": "TST", "type": "Certidão Negativa de Débitos Trabalhistas", "portal": "https://cndt-certidao.tst.jus.br/"},
    "cgu": {"name": "CGU", "type": "Certidões Correcionais e de Sanções", "portal": "https://certidoes.cgu.gov.br/"},
    "onr": {"name": "ONR", "type": "Certidão de Registro de Imóveis", "portal": "https://www.ridigital.org.br/"},
}

_storage_secret = os.getenv("CERTIFICATES_STORAGE_KEY") or KEALEX_SECRET_KEY
_document_cipher = Fernet(base64.urlsafe_b64encode(hashlib.sha256((_storage_secret + ":certificate-documents:v1").encode()).digest()))
PROVIDERS["receita-federal"]["portal"] = "https://www.gov.br/pt-br/servicos/emitir-certidao-de-regularidade-fiscal-perante-a-fazenda-nacional"

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


def _mode(provider: str) -> str:
    if os.getenv("CERTIFICATES_ENABLED", "true").lower() not in {"1", "true", "yes", "on"}:
        return "UNAVAILABLE"
    if os.getenv(API_FLAGS[provider], "false").lower() in {"1", "true", "yes", "on"}:
        # API mode requires an implemented provider and credentials. None are enabled by this module.
        return "OFFICIAL_PORTAL"
    return "OFFICIAL_PORTAL"


def provider_catalog():
    result = []
    for key, provider in PROVIDERS.items():
        mode = _mode(key)
        result.append({"id": key, **provider, "integrationMode": mode, "apiAvailable": False, "portalAvailable": mode == "OFFICIAL_PORTAL", "portalUrl": provider["portal"]})
    return result


def requirements_for(provider: str):
    if provider not in PROVIDERS:
        raise HTTPException(404, "Emissor não encontrado")
    return {"provider": provider, "fields": REQUIREMENTS[provider], "integrationMode": _mode(provider)}


def availability_for(provider: str):
    config = next((item for item in provider_catalog() if item["id"] == provider), None)
    if not config:
        raise HTTPException(404, "Emissor não encontrado")
    return {"provider": provider, "available": config["portalAvailable"], "integrationMode": config["integrationMode"], "apiAvailable": False, "message": "A emissão automatizada não está habilitada. Continue no portal oficial e anexe o PDF obtido para mantê-lo neste histórico.", "portalUrl": config["portalUrl"]}


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


def create_request(db: Session, payload: dict, provider: str, fields: dict):
    if provider not in PROVIDERS:
        raise HTTPException(404, "Emissor não encontrado")
    if _mode(provider) == "UNAVAILABLE":
        raise HTTPException(503, "Módulo de certidões desabilitado")
    _validate_request(provider, fields)
    identifier = _digits(fields.get("document", "")) or str(fields.get("matricula", "")).strip()
    row = CertificateRequest(
        id=str(uuid.uuid4()), tenant_id=str(payload["tenant_id"]), user_id=str(payload["sub"]),
        provider=provider, certificate_type=PROVIDERS[provider]["type"],
        subject_type="CPF" if len(identifier) == 11 else "CNPJ" if len(identifier) == 14 else "IMOVEL",
        subject_identifier_masked=_mask(identifier), subject_identifier_hash=hmac.new(_storage_secret.encode(), identifier.encode(), hashlib.sha256).hexdigest(),
        request_payload="{}", status="MANUAL_ACTION_REQUIRED", portal_url=PROVIDERS[provider]["portal"],
    )
    db.add(row)
    _audit(db, row, str(payload["sub"]), "request_created")
    db.commit()
    db.refresh(row)
    return serialize_request(row)


def serialize_request(row: CertificateRequest):
    document = getattr(row, "document", None)
    return {"id": row.id, "protocol": row.external_protocol or row.id, "provider": row.provider, "certificateType": row.certificate_type, "subjectType": row.subject_type, "subjectIdentifierMasked": row.subject_identifier_masked, "status": row.status, "portalUrl": row.portal_url, "createdAt": row.created_at.isoformat() if row.created_at else None, "updatedAt": row.updated_at.isoformat() if row.updated_at else None, "completedAt": row.completed_at.isoformat() if row.completed_at else None, "documentAvailable": bool(document), "documentSource": document.upload_source if document else None, "validationStatus": document.validation_status if document else None, "expiresAt": document.expires_at.isoformat() if document and document.expires_at else None}


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
    # Um upload do usuário não confirma autenticidade oficial nem a emissão.
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

