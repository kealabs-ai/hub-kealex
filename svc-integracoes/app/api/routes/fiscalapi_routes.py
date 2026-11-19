from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.application.use_cases.fiscalapi_certificates import (
    create_consultation,
    get_consultation,
    get_consultation_document,
)
from app.infrastructure.database.session import get_db
from app.infrastructure.security.jwt_provider import verify_token


router = APIRouter(prefix="/api/v1/certidoes", tags=["fiscalapi-certidoes"])
ALLOWED_ROLES = {"admin", "advogado", "juridico", "escritorio"}


class FiscalApiInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ConsultaIEIn(FiscalApiInput):
    uf: str = Field(min_length=2, max_length=2)
    cpf: str | None = Field(default=None, max_length=20)
    cnpj: str | None = Field(default=None, max_length=24)
    ie: str | None = Field(default=None, max_length=30)
    secundarias: bool = False


class EnriquecimentoIn(FiscalApiInput):
    tipo: Literal["cnpj", "simples_nacional"]
    cnpj: str = Field(min_length=14, max_length=24)
    force_fresh: bool = False


class CndEstadualIn(FiscalApiInput):
    uf: str = Field(min_length=2, max_length=2)
    cpf: str | None = Field(default=None, max_length=20)
    cnpj: str | None = Field(default=None, max_length=24)


class CertidoesFederaisIn(FiscalApiInput):
    tipo: Literal["cndt", "crf_fgts", "cnd_federal"]
    cpf: str | None = Field(default=None, max_length=20)
    cnpj: str | None = Field(default=None, max_length=24)
    emitir_nova: bool = False


class SigefIn(FiscalApiInput):
    cpf: str | None = Field(default=None, max_length=20)
    cnpj: str | None = Field(default=None, max_length=24)


def _identity(payload: dict) -> tuple[str, str]:
    if payload.get("role") not in ALLOWED_ROLES:
        raise HTTPException(403, "Acesso não permitido.")
    tenant_id, user_id = payload.get("tenant_id"), payload.get("sub")
    if not tenant_id or not user_id:
        raise HTTPException(403, "Conta sem organização associada.")
    return str(tenant_id), str(user_id)


def _run(service: str, body: FiscalApiInput, key: str | None, payload: dict, db: Session):
    tenant_id, user_id = _identity(payload)
    if not key:
        raise HTTPException(422, "Informe Idempotency-Key para evitar consultas duplicadas.")
    return create_consultation(db, tenant_id, user_id, service, body.model_dump(exclude_none=True), key)


@router.post("/consulta-ie")
def consulta_ie(
    body: ConsultaIEIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    payload=Depends(verify_token),
    db: Session = Depends(get_db),
):
    return _run("consulta-ie", body, idempotency_key, payload, db)


@router.post("/enriquecimento")
def enriquecimento(
    body: EnriquecimentoIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    payload=Depends(verify_token),
    db: Session = Depends(get_db),
):
    return _run("enriquecimento", body, idempotency_key, payload, db)


@router.post("/cnd-estadual")
def cnd_estadual(
    body: CndEstadualIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    payload=Depends(verify_token),
    db: Session = Depends(get_db),
):
    return _run("cnd-estadual", body, idempotency_key, payload, db)


@router.post("/federais")
def certidoes_federais(
    body: CertidoesFederaisIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    payload=Depends(verify_token),
    db: Session = Depends(get_db),
):
    return _run("federais", body, idempotency_key, payload, db)


@router.post("/sigef")
def sigef(
    body: SigefIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    payload=Depends(verify_token),
    db: Session = Depends(get_db),
):
    return _run("sigef", body, idempotency_key, payload, db)


@router.get("/consultas/{consultation_id}")
def consulta(consultation_id: str, payload=Depends(verify_token), db: Session = Depends(get_db)):
    tenant_id, user_id = _identity(payload)
    return get_consultation(db, tenant_id, user_id, consultation_id)


@router.get("/consultas/{consultation_id}/documento")
def documento(consultation_id: str, payload=Depends(verify_token), db: Session = Depends(get_db)):
    tenant_id, user_id = _identity(payload)
    content, filename = get_consultation_document(db, tenant_id, user_id, consultation_id)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
