import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.core.config import ESCAVADOR_API_ENABLED, ESCAVADOR_API_TIMEOUT, ESCAVADOR_API_TOKEN
from app.infrastructure.escavador_adapter import EscavadorAdapter, EscavadorError
from app.infrastructure.security.jwt_provider import verify_token


router = APIRouter(prefix="/api/v1/escavador", tags=["escavador-processos"])
ALLOWED_ROLES = {"admin", "advogado", "juridico", "escritorio"}
CNJ_PATTERN = re.compile(r"^\d{20}$")


def _identity(payload: dict) -> None:
    if payload.get("role") not in ALLOWED_ROLES:
        raise HTTPException(403, "Acesso não permitido.")
    if not payload.get("tenant_id") or not payload.get("sub"):
        raise HTTPException(403, "Conta sem organização associada.")


@router.get("/processos/{numero_cnj}")
def consultar_processo(numero_cnj: str, payload=Depends(verify_token)):
    _identity(payload)
    normalized = re.sub(r"\D", "", numero_cnj)
    if not CNJ_PATTERN.fullmatch(normalized):
        raise HTTPException(422, "Informe o número CNJ completo, com 20 dígitos.")
    adapter = EscavadorAdapter(
        token=ESCAVADOR_API_TOKEN,
        enabled=ESCAVADOR_API_ENABLED,
        timeout=ESCAVADOR_API_TIMEOUT,
    )
    try:
        result, credits_used = adapter.consultar_processo(normalized)
    except EscavadorError as exc:
        headers = {"Retry-After": exc.retry_after} if exc.retry_after else None
        raise HTTPException(exc.status_code, {"code": exc.code, "message": exc.message}, headers=headers) from exc
    result["_integracao"] = {"creditosUtilizadosCentavos": credits_used}
    return JSONResponse(content=result, headers={"Cache-Control": "no-store"})