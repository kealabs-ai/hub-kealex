import json
import re
import uuid
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request as URLRequest, urlopen

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import auth_guard
from app.infrastructure.database.models.processo_model import HistoricoConsultaProcessual, ProcessoAcompanhado
from app.infrastructure.database.session import get_db

router = APIRouter(prefix="/k1/lex/processos-acompanhados", tags=["processos-acompanhados"])
CNJ = re.compile(r"^\d{20}$")
ALLOWED_ROLES = {"admin", "advogado", "juridico", "escritorio"}


class ConsultaIn(BaseModel):
    numero_processo: str


def _normalizar_cnj(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if not CNJ.fullmatch(digits):
        raise HTTPException(422, "Informe o n?mero CNJ completo, com 20 d?gitos.")
    check = int(digits[:7] + digits[9:] + "00")
    if 98 - check % 97 != int(digits[7:9]):
        raise HTTPException(422, "O d?gito verificador do n?mero CNJ ? inv?lido.")
    return digits


def _scope(payload: dict) -> str:
    role = payload.get("role")
    if role not in ALLOWED_ROLES:
        raise HTTPException(403, "Acesso n?o permitido.")
    tenant_id, user_id = payload.get("tenant_id"), payload.get("sub")
    if not tenant_id or not user_id:
        raise HTTPException(403, "Conta sem organiza??o associada.")
    return user_id if role == "advogado" else tenant_id


def _iso(value):
    return value.isoformat() if isinstance(value, datetime) else value


def _serialize(row: ProcessoAcompanhado) -> dict:
    return {
        "id": row.id, "numero_processo": row.numero_processo, "tribunal": row.tribunal,
        "classe_processual": row.classe_processual, "assunto": row.assunto,
        "fase_atual": row.fase_atual, "situacao": row.situacao,
        "data_ultima_movimentacao": row.data_ultima_movimentacao,
        "ultima_consulta_em": _iso(row.ultima_consulta_em), "dados": row.dados or {},
    }


def _consultar_fornecedor(numero: str, authorization: str) -> dict:
    url = f"http://svc-integracoes:8000/api/v1/escavador/processos/{numero}"
    request = URLRequest(url, headers={"Authorization": authorization, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=40) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            error_body = json.loads(exc.read().decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            error_body = {}
        detail = error_body.get("detail", {})
        if isinstance(detail, dict):
            detail = detail.get("message") or detail.get("code")
        message = detail if isinstance(detail, str) else "N?o foi poss?vel consultar o processo na integra??o."
        raise HTTPException(exc.code, message) from exc
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise HTTPException(503, "A integra??o processual est? temporariamente indispon?vel.") from exc
    if not isinstance(body, dict):
        raise HTTPException(502, "A integra??o retornou dados inv?lidos para o processo.")
    returned = re.sub(r"\D", "", str(body.get("numero_cnj") or ""))
    valid_data = bool(body.get("fontes") or body.get("tribunal") or body.get("envolvidos") or body.get("data_inicio"))
    if returned != numero or not valid_data:
        raise HTTPException(404, "Nenhum processo v?lido foi encontrado para o n?mero informado.")
    return body


def _nonempty(value):
    return value is not None and value != "" and value != [] and value != {}


def _list_identity(item: dict):
    if item.get("sigla"):
        return ("fonte", item.get("sigla"), item.get("grau_formatado"))
    if item.get("numero_cnj"):
        return ("cnj", item.get("numero_cnj"))
    if item.get("id") or item.get("codigo"):
        return ("id", item.get("id") or item.get("codigo"))
    if item.get("data") and (item.get("nome") or item.get("descricao")):
        return ("mov", item.get("data"), item.get("nome") or item.get("descricao"))
    return None


def _merge_value(old, new):
    if isinstance(old, dict) and isinstance(new, dict):
        merged = dict(old)
        for key, value in new.items():
            if key in merged:
                merged[key] = _merge_value(merged[key], value)
            elif _nonempty(value):
                merged[key] = value
        return merged
    if isinstance(old, list) and isinstance(new, list):
        merged = list(old)
        for item in new:
            identity = _list_identity(item) if isinstance(item, dict) else None
            index = next((i for i, previous in enumerate(merged)
                          if (identity is not None and isinstance(previous, dict) and _list_identity(previous) == identity)
                          or (identity is None and previous == item)), None)
            if index is None:
                merged.append(item)
            else:
                merged[index] = _merge_value(merged[index], item)
        return merged
    return new if _nonempty(new) else old


def _merge(old: dict, new: dict) -> dict:
    return _merge_value(old or {}, new or {})


def _fields(data: dict) -> dict:
    fontes = data.get("fontes") if isinstance(data.get("fontes"), list) else []
    fonte = fontes[0] if fontes and isinstance(fontes[0], dict) else {}
    capa = fonte.get("capa") if isinstance(fonte.get("capa"), dict) else {}
    tribunal = data.get("tribunal") if isinstance(data.get("tribunal"), dict) else {}
    dates = [
        movement.get("data") or movement.get("data_movimentacao")
        for source in fontes if isinstance(source, dict)
        for movement in (source.get("movimentacoes") or []) if isinstance(movement, dict)
        if isinstance(movement.get("data") or movement.get("data_movimentacao"), str)
    ]
    dates.extend([data["data_ultima_movimentacao"]] if isinstance(data.get("data_ultima_movimentacao"), str) else [])
    latest_movement = max(dates, default=None)
    return {
        "tribunal": tribunal.get("sigla") or tribunal.get("nome") or fonte.get("sigla") or fonte.get("nome"),
        "classe_processual": capa.get("classe"), "assunto": capa.get("assunto"),
        "fase_atual": data.get("fase_atual") or fonte.get("fase_atual"),
        "situacao": capa.get("situacao") or data.get("situacao") or fonte.get("status_predito"),
        "data_ultima_movimentacao": latest_movement,
    }


def _audit(db, payload, numero, process_id, status_http, result, changed, last_movement):
    db.add(HistoricoConsultaProcessual(
        id=str(uuid.uuid4()), tenant_id=payload["tenant_id"], processo_id=process_id,
        numero_processo=numero, usuario_solicitante_id=payload["sub"], fornecedor="escavador",
        status_http=status_http, status_consulta=result,
        houve_alteracao=None if changed is None else int(changed),
        data_ultima_movimentacao=last_movement, consultado_em=datetime.utcnow(),
    ))


def _sync(db: Session, numero: str, request: Request, payload: dict, current=None):
    scope_key = _scope(payload)
    if current is None:
        current = db.query(ProcessoAcompanhado).filter_by(
            tenant_id=payload["tenant_id"], scope_key=scope_key, numero_processo=numero
        ).with_for_update().first()
    try:
        fresh = _consultar_fornecedor(numero, request.headers.get("authorization", ""))
    except HTTPException as exc:
        _audit(db, payload, numero, current.id if current else None, exc.status_code, "erro", None,
               current.data_ultima_movimentacao if current else None)
        db.commit()
        raise

    old_data = (current.dados or {}) if current else {}
    merged = _merge(old_data, fresh)
    changed = current is None or merged != old_data
    now = datetime.utcnow()
    if current is None:
        current = ProcessoAcompanhado(
            id=str(uuid.uuid4()), tenant_id=payload["tenant_id"], user_id=payload["sub"],
            scope_key=scope_key, numero_processo=numero, dados=merged,
            ultima_consulta_em=now, created_at=now, updated_at=now,
        )
        db.add(current)
    else:
        current.dados = merged
        current.ultima_consulta_em = now
        current.updated_at = now
    for name, value in _fields(merged).items():
        if _nonempty(value):
            setattr(current, name, value)
    _audit(db, payload, numero, current.id, 200, "sucesso", changed, current.data_ultima_movimentacao)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        current = db.query(ProcessoAcompanhado).filter_by(
            tenant_id=payload["tenant_id"], scope_key=scope_key, numero_processo=numero
        ).with_for_update().first()
        if current is None:
            raise
        old_data = current.dados or {}
        current.dados = _merge(old_data, fresh)
        current.ultima_consulta_em = now
        current.updated_at = now
        for name, value in _fields(current.dados).items():
            if _nonempty(value):
                setattr(current, name, value)
        _audit(db, payload, numero, current.id, 200, "sucesso", current.dados != old_data, current.data_ultima_movimentacao)
        db.commit()
    db.refresh(current)
    return _serialize(current)


@router.get("")
def list_processos(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                   search: str | None = None, tribunal: str | None = None, fase: str | None = None,
                   situacao: str | None = None, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    scope_key = _scope(payload)
    base = db.query(ProcessoAcompanhado).filter(ProcessoAcompanhado.tenant_id == payload["tenant_id"])
    if payload.get("role") == "advogado":
        base = base.filter(ProcessoAcompanhado.scope_key == scope_key)
    filters = {}
    for key, column in (
        ("tribunais", ProcessoAcompanhado.tribunal),
        ("fases", ProcessoAcompanhado.fase_atual),
        ("situacoes", ProcessoAcompanhado.situacao),
    ):
        values = base.with_entities(column).filter(column.isnot(None), column != "").distinct().all()
        filters[key] = sorted(row[0] for row in values)
    query = base
    if search:
        search_digits = re.sub(r"\D", "", search)
        query = query.filter(ProcessoAcompanhado.numero_processo.like(f"%{search_digits}%"))
    if tribunal:
        query = query.filter(ProcessoAcompanhado.tribunal == tribunal)
    if fase:
        query = query.filter(ProcessoAcompanhado.fase_atual == fase)
    if situacao:
        query = query.filter(ProcessoAcompanhado.situacao == situacao)
    total = query.count()
    rows = query.order_by(desc(ProcessoAcompanhado.ultima_consulta_em)).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_serialize(row) for row in rows], "total": total, "page": page, "page_size": page_size, "filters": filters}


@router.post("/consultar")
def consultar_processo(body: ConsultaIn, request: Request, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    return _sync(db, _normalizar_cnj(body.numero_processo), request, payload)


@router.post("/{processo_id}/atualizar")
def atualizar_processo(processo_id: str, request: Request, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    scope_key = _scope(payload)
    query = db.query(ProcessoAcompanhado).filter_by(id=processo_id, tenant_id=payload["tenant_id"])
    if payload.get("role") == "advogado":
        query = query.filter_by(scope_key=scope_key)
    current = query.with_for_update().first()
    if not current:
        raise HTTPException(404, "Processo acompanhado n?o encontrado.")
    return _sync(db, current.numero_processo, request, payload, current)


@router.get("/{processo_id}")
def get_processo(processo_id: str, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    scope_key = _scope(payload)
    query = db.query(ProcessoAcompanhado).filter_by(id=processo_id, tenant_id=payload["tenant_id"])
    if payload.get("role") == "advogado":
        query = query.filter_by(scope_key=scope_key)
    current = query.first()
    if not current:
        raise HTTPException(404, "Processo acompanhado n?o encontrado.")
    return _serialize(current)


@router.get("/{processo_id}/historico")
def historico_processo(processo_id: str, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    scope_key = _scope(payload)
    visible = db.query(ProcessoAcompanhado).filter_by(id=processo_id, tenant_id=payload["tenant_id"])
    if payload.get("role") == "advogado":
        visible = visible.filter_by(scope_key=scope_key)
    if not visible.first():
        raise HTTPException(404, "Processo acompanhado n?o encontrado.")
    rows = db.query(HistoricoConsultaProcessual).filter_by(
        processo_id=processo_id, tenant_id=payload["tenant_id"]
    ).order_by(desc(HistoricoConsultaProcessual.consultado_em)).limit(100).all()
    return [{
        "id": row.id, "consultado_em": _iso(row.consultado_em), "fornecedor": row.fornecedor,
        "status_http": row.status_http, "status_consulta": row.status_consulta,
        "houve_alteracao": bool(row.houve_alteracao) if row.houve_alteracao is not None else None,
        "data_ultima_movimentacao": row.data_ultima_movimentacao,
    } for row in rows]
