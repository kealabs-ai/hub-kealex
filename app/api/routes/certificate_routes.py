from email.parser import BytesParser
from email.policy import default

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.application.use_cases.certificates import (PROVIDERS, availability_for, create_request, document_content, get_owned_request, list_requests, provider_catalog, requirements_for, serialize_request, upload_document)
from app.infrastructure.database.models import CertificateAuditLog, CertificateDocument
from app.infrastructure.database.session import get_db
from app.infrastructure.security.jwt_provider import verify_token

router = APIRouter(prefix="/api/v1/certificates", tags=["certificates"])


class CertificateRequestIn(BaseModel):
    provider: str = Field(min_length=2, max_length=40)
    fields: dict[str, str] = Field(default_factory=dict)

    @field_validator("fields")
    @classmethod
    def bound_fields(cls, values):
        if len(values) > 20 or any(len(name) > 40 or len(value) > 250 for name, value in values.items()):
            raise ValueError("A solicitação excede os limites de campos")
        return values


def _identity(payload):
    if payload.get("role") not in {"admin", "advogado", "juridico", "escritorio"}:
        raise HTTPException(403, "Acesso não permitido")
    return str(payload["tenant_id"]), str(payload["sub"])


@router.get("/providers")
def providers(payload=Depends(verify_token)):
    _identity(payload)
    return provider_catalog()


@router.get("/providers/{provider}/availability")
def provider_availability(provider: str, payload=Depends(verify_token)):
    _identity(payload)
    return availability_for(provider)


@router.get("/providers/{provider}/requirements")
def provider_requirements(provider: str, payload=Depends(verify_token)):
    _identity(payload)
    return requirements_for(provider)


@router.post("/requests", status_code=201)
def request_certificate(body: CertificateRequestIn, payload=Depends(verify_token), db: Session = Depends(get_db)):
    _identity(payload)
    return create_request(db, payload, body.provider, body.fields)


@router.get("/requests")
def requests(provider: str | None = None, status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), sort_by: str = "created_at", sort_order: str = "desc", payload=Depends(verify_token), db: Session = Depends(get_db)):
    tenant_id, user_id = _identity(payload)
    if sort_by not in {"created_at", "updated_at", "status", "provider"} or sort_order not in {"asc", "desc"}:
        raise HTTPException(422, "Ordenação inválida")
    return list_requests(db, tenant_id, user_id, provider, status, page, page_size, sort_by, sort_order)


@router.get("/requests/{request_id}")
def request_details(request_id: str, payload=Depends(verify_token), db: Session = Depends(get_db)):
    tenant_id, user_id = _identity(payload)
    return serialize_request(get_owned_request(db, tenant_id, user_id, request_id))


@router.get("/requests/{request_id}/status")
def request_status(request_id: str, payload=Depends(verify_token), db: Session = Depends(get_db)):
    tenant_id, user_id = _identity(payload)
    row = get_owned_request(db, tenant_id, user_id, request_id)
    return {"id": row.id, "status": row.status, "updatedAt": row.updated_at.isoformat() if row.updated_at else None, "documentAvailable": bool(row.document)}


@router.post("/requests/{request_id}/document", status_code=201)
async def attach_document(request_id: str, request: Request, payload=Depends(verify_token), db: Session = Depends(get_db)):
    tenant_id, user_id = _identity(payload)
    row = get_owned_request(db, tenant_id, user_id, request_id)
    content_type = request.headers.get("content-type", "")
    if not content_type.lower().startswith("multipart/form-data;"):
        raise HTTPException(415, "Envie o arquivo como multipart/form-data")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 10 * 1024 * 1024 + 65536:
            raise HTTPException(413, "O upload excede o limite de 10 MB")
    message = BytesParser(policy=default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + bytes(body)
    )
    upload = next((part for part in message.iter_parts() if part.get_content_disposition() == "form-data" and part.get_param("name", header="content-disposition") == "file"), None)
    if not upload or upload.get_content_type() != "application/pdf":
        raise HTTPException(415, "Envie um arquivo PDF no campo file")
    content = upload.get_payload(decode=True) or b""
    upload_document(db, row, user_id, upload.get_filename() or "certidao.pdf", content)
    return {"requestId": row.id, "documentAvailable": True, "source": "user_upload", "validationStatus": "unverified"}


@router.get("/{request_id}/document")
@router.get("/{request_id}/download")
def download_document(request_id: str, request: Request, payload=Depends(verify_token), db: Session = Depends(get_db)):
    tenant_id, user_id = _identity(payload)
    row = get_owned_request(db, tenant_id, user_id, request_id)
    document = db.query(CertificateDocument).filter_by(request_id=row.id).first()
    if not document:
        raise HTTPException(404, "O PDF ainda não está disponível para esta solicitação")
    download = request.url.path.endswith("/download")
    db.add(CertificateAuditLog(request_id=row.id, tenant_id=tenant_id, user_id=user_id, action="document_downloaded" if download else "document_viewed", status=row.status))
    db.commit()
    disposition = "attachment" if download else "inline"
    return Response(content=document_content(document), media_type="application/pdf", headers={"Content-Disposition": f'{disposition}; filename="{document.filename}"', "X-Document-Source": document.upload_source, "X-Document-Validation": document.validation_status, "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})


@router.post("/{request_id}/validate")
def validate_document(request_id: str, payload=Depends(verify_token), db: Session = Depends(get_db)):
    tenant_id, user_id = _identity(payload)
    row = get_owned_request(db, tenant_id, user_id, request_id)
    document = db.query(CertificateDocument).filter_by(request_id=row.id).first()
    if not document:
        raise HTTPException(409, "Nenhum PDF foi anexado a esta solicitação")
    db.add(CertificateAuditLog(request_id=row.id, tenant_id=tenant_id, user_id=user_id, action="validation_requested", status=row.status))
    db.commit()
    return {"supported": False, "valid": None, "status": "UNAVAILABLE", "message": "O arquivo foi enviado pelo usuário e ainda não foi validado no serviço oficial do emissor.", "source": document.upload_source, "fileHash": document.file_hash}
