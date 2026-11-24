import json
import re
from urllib.error import HTTPError as URLHTTPError, URLError
from urllib.request import urlopen
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.api.dependencies import client_access_guard
from app.api.schemas.client_schema import ClienteIn, ClienteUpdate, ClienteGetIn, ClienteDeleteIn
from app.application.use_cases.client_presenter import client_to_dict
from app.infrastructure.database.models.client_model import Cliente
from app.infrastructure.database.session import get_db

router = APIRouter()


@router.get("/k1/lex/clientes/cep/{cep}")
@router.get("/clientes/cep/{cep}")
def lookup_cep(cep: str, payload=Depends(client_access_guard)):
    digits = re.sub(r"\D", "", cep)
    if len(digits) != 8:
        raise HTTPException(422, "Informe um CEP válido com 8 dígitos")
    try:
        with urlopen(f"https://viacep.com.br/ws/{digits}/json/", timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (URLHTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise HTTPException(502, "Não foi possível consultar o CEP agora") from exc
    if result.get("erro"):
        raise HTTPException(404, "CEP não encontrado")
    return {
        "cep": result.get("cep", digits),
        "endereco": result.get("logradouro", ""),
        "cidade": result.get("localidade", ""),
        "estado": result.get("uf", ""),
    }

@router.get("/k1/lex/clientes")
@router.get("/clientes")
def list_clientes(db: Session = Depends(get_db), payload=Depends(client_access_guard)):
    tid  = payload.get("tenant_id")
    role = payload.get("role")
    uid  = payload.get("sub")
    q = db.query(Cliente).filter_by(tenant_id=tid)
    if role == "advogado":
        q = q.filter_by(advogado_id=uid)
    return [client_to_dict(c) for c in q.all()]


@router.post("/k1/lex/clientes/get")
@router.post("/clientes/get")
def get_cliente(body: ClienteGetIn, db: Session = Depends(get_db), payload=Depends(client_access_guard)):
    tid = payload.get("tenant_id")
    q = db.query(Cliente).filter_by(id=body.id, tenant_id=tid)
    if payload.get("role") == "advogado":
        q = q.filter_by(advogado_id=payload.get("sub"))
    c = q.first()
    if not c:
        raise HTTPException(404, "Não encontrado")
    return client_to_dict(c)


@router.post("/k1/lex/clientes", status_code=201)
@router.post("/clientes", status_code=201)
def create_cliente(body: ClienteIn, db: Session = Depends(get_db), payload=Depends(client_access_guard)):
    tid = payload.get("tenant_id")
    uid = payload.get("sub")
    if db.query(Cliente).filter_by(email=body.email, tenant_id=tid).first():
        raise HTTPException(409, "Email já cadastrado")
    c = Cliente(
        tenant_id=tid, advogado_id=uid,
        nome=body.nome, email=body.email, telefone=body.telefone,
        cpf_cnpj=body.cpfCnpj, cep=body.cep, endereco=body.endereco,
        cidade=body.cidade, estado=body.estado, observacoes=body.observacoes,
    )
    db.add(c); db.commit(); db.refresh(c)
    return client_to_dict(c)


@router.post("/k1/lex/clientes/update")
@router.post("/clientes/update")
def update_cliente(body: ClienteUpdate, db: Session = Depends(get_db), payload=Depends(client_access_guard)):
    tid = payload.get("tenant_id")
    q = db.query(Cliente).filter_by(id=body.id, tenant_id=tid)
    if payload.get("role") == "advogado":
        q = q.filter_by(advogado_id=payload.get("sub"))
    c = q.first()
    if not c:
        raise HTTPException(404, "Não encontrado")
    data = body.model_dump(exclude_unset=True, exclude_none=True, exclude={"id"})
    if "email" in data and data["email"] != c.email:
        duplicate = db.query(Cliente).filter(
            Cliente.tenant_id == tid, Cliente.email == data["email"], Cliente.id != c.id
        ).first()
        if duplicate:
            raise HTTPException(409, "Este e-mail j? est? cadastrado para outro cliente.")

    field_map = {"cpfCnpj": "cpf_cnpj"}
    allowed_fields = {"nome", "email", "telefone", "cpf_cnpj", "cep", "endereco", "cidade", "estado", "observacoes"}
    for key, value in data.items():
        field = field_map.get(key, key)
        if field not in allowed_fields:
            continue
        setattr(c, field, value)
    c.updated_at = datetime.utcnow()
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "N?o foi poss?vel salvar: verifique se o e-mail j? est? em uso.") from exc
    db.refresh(c)
    return client_to_dict(c)


@router.post("/k1/lex/clientes/delete")
@router.post("/clientes/delete")
def delete_cliente(body: ClienteDeleteIn, db: Session = Depends(get_db), payload=Depends(client_access_guard)):
    tid = payload.get("tenant_id")
    q = db.query(Cliente).filter_by(id=body.id, tenant_id=tid)
    if payload.get("role") == "advogado":
        q = q.filter_by(advogado_id=payload.get("sub"))
    c = q.first()
    if not c:
        raise HTTPException(404, "Não encontrado")
    db.delete(c); db.commit()
    return {"ok": True}
