import hashlib
import hmac
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import _require_admin
from app.core.config import KEALEX_SECRET_KEY
from app.domain.entities.enums import StatusEnum
from app.infrastructure.database.models import Cliente, FiscalApiConsulta, Honorario, KeaCreditsWallet, Processo, Usuario
from app.infrastructure.database.session import get_db

router = APIRouter()


def _client_identifier_hash(value: str | None) -> tuple[str | None, str | None]:
    normalized = re.sub(r"[^A-Za-z0-9]", "", value or "").upper()
    if not normalized:
        return None, None
    kind = "cpf" if len(normalized) == 11 and normalized.isdigit() else "cnpj"
    digest = hmac.new(KEALEX_SECRET_KEY.encode(), normalized.encode(), hashlib.sha256).hexdigest()
    return kind, digest


@router.get("/k1/lex/gestao/dashboard", tags=["gestao"])
def gestao_dashboard(db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(403, "Conta sem organização associada")

    processos_ativos = db.query(func.count(Processo.id)).filter(
        Processo.tenant_id == tenant_id,
        Processo.status == StatusEnum.ativo,
    ).scalar() or 0
    usuarios = db.query(func.count(Usuario.id)).filter(Usuario.tenant_id == tenant_id).scalar() or 0
    carteira = db.query(KeaCreditsWallet).filter_by(organizacao_id=tenant_id).first()
    consultas = db.query(FiscalApiConsulta).filter_by(tenant_id=tenant_id, provider="fiscalapi").all()

    clientes = db.query(Cliente).filter(
        Cliente.tenant_id == tenant_id,
        Cliente.cpf_cnpj.isnot(None),
    ).all()
    client_by_subject: dict[tuple[str, str], Cliente] = {}
    for client in clientes:
        kind, digest = _client_identifier_hash(client.cpf_cnpj)
        if kind and digest:
            client_by_subject[(kind, digest)] = client

    counts_by_client: dict[str, dict] = {}
    for consultation in consultas:
        client = client_by_subject.get((consultation.subject_type or "", consultation.subject_hash or ""))
        if client:
            entry = counts_by_client.setdefault(client.id, {"clienteId": client.id, "nome": client.nome, "quantidade": 0})
            entry["quantidade"] += 1

    honorarios = db.query(Honorario).filter_by(tenant_id=tenant_id).all()
    total_pago = sum(item.valor_centavos for item in honorarios if item.status == "pago")
    total_pendente = sum(item.valor_centavos for item in honorarios if item.status == "pendente")
    total_vencido = sum(item.valor_centavos for item in honorarios if item.status == "vencido")

    top_clientes = sorted(counts_by_client.values(), key=lambda item: (-item["quantidade"], item["nome"].casefold()))[:10]
    return {
        "processosAtivos": processos_ativos,
        "usuariosCadastrados": usuarios,
        "keaCreditsDisponivel": carteira.saldo_creditos if carteira else 0,
        "consultasTotal": len(consultas),
        "consultasPorFornecedor": {"fiscalapi": len(consultas), "escavador": 0},
        "topClientesConsultas": top_clientes,
        "financeiro": {
            "totalPago": total_pago,
            "totalPendente": total_pendente,
            "totalVencido": total_vencido,
            "totalGeral": total_pago + total_pendente + total_vencido,
        },
    }