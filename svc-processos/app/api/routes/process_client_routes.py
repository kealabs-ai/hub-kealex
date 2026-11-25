import uuid
from typing import Union

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import auth_guard
from app.api.schemas.process_schema import (
    ProcessoClienteIn, ProcessoClienteUpdate, ProcessoClientesReplaceIn, ProcessoParteIn, ProcessoPartesReplaceIn,
)
from app.application.use_cases.process_access import _scoped_process
from app.infrastructure.database.models.processo_model import Cliente, ProcessClient, ProcessParty
from app.infrastructure.database.session import get_db

router = APIRouter()


def _client_query(db: Session, payload):
    q = db.query(Cliente).filter(Cliente.tenant_id == payload.get("tenant_id"))
    if payload.get("role") == "advogado":
        q = q.filter(Cliente.advogado_id == payload.get("sub"))
    return q


def _client_dict(client: Cliente):
    return {
        "id": client.id, "nome": client.nome, "email": client.email,
        "telefone": client.telefone, "cpfCnpj": client.cpf_cnpj,
        "cep": getattr(client, "cep", None), "endereco": client.endereco,
        "cidade": getattr(client, "cidade", None), "estado": getattr(client, "estado", None),
        "rg": client.rg, "orgaoExpedidor": client.orgao_expedidor,
        "nacionalidade": client.nacionalidade, "estadoCivil": client.estado_civil,
        "profissao": client.profissao, "dataNascimento": client.data_nascimento,
        "razaoSocial": client.razao_social, "nomeFantasia": client.nome_fantasia,
        "inscricaoEstadual": client.inscricao_estadual,
        "inscricaoMunicipal": client.inscricao_municipal,
        "representanteLegal": client.representante_legal, "whatsapp": client.whatsapp,
    }


def _link_dict(link: ProcessClient, client: Cliente):
    return {
        **_client_dict(client), "linkId": link.id,
        "proceduralRole": link.posicao_processual, "proceduralPole": link.polo_processual,
        "isPrimary": bool(link.cliente_principal), "qualificationSnapshot": link.snapshot_qualificacao,
        "notes": link.observacoes,
    }


@router.get("/k1/lex/processos/{process_id}/clients")
def list_process_clients(process_id: str, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    process = _scoped_process(db, process_id, payload)
    if not process:
        raise HTTPException(404, "Processo não encontrado")
    links = db.query(ProcessClient).filter_by(processo_id=process.id, tenant_id=process.tenant_id, ativo=1).all()
    linked_ids = {link.cliente_id for link in links}
    # Migração gradual: processos antigos ganham representação compatível mesmo antes do backfill.
    if process.cliente_id and process.cliente_id not in linked_ids:
        client = _client_query(db, payload).filter(Cliente.id == process.cliente_id).first()
        if client:
            links.append(ProcessClient(id="legacy-" + client.id, tenant_id=process.tenant_id,
                processo_id=process.id, cliente_id=client.id, posicao_processual="Interessado",
                polo_processual=None, cliente_principal=1, snapshot_qualificacao=None,
                observacoes=None, criado_por=process.user_id, ativo=1))
            return [_link_dict(links[-1], client)]
    clients = {c.id: c for c in _client_query(db, payload).filter(Cliente.id.in_(linked_ids)).all()} if linked_ids else {}
    return [_link_dict(link, clients[link.cliente_id]) for link in links if link.cliente_id in clients]


def _save_links(process_id: str, body: ProcessoClientesReplaceIn, db: Session, payload):
    process = _scoped_process(db, process_id, payload)
    if not process:
        raise HTTPException(404, "Processo não encontrado")
    if payload.get("role") == "cliente":
        raise HTTPException(403, "Acesso negado")
    items = body.clientes
    if not items:
        raise HTTPException(422, "Mantenha ao menos um cliente vinculado ao processo")
    if len({item.clienteId for item in items}) != len(items):
        raise HTTPException(422, "Não repita clientes no mesmo processo")
    primary = next((item for item in items if item.isPrimary), None)
    if not primary and items:
        primary = items[0]
    clients = {}
    for item in items:
        client = _client_query(db, payload).filter(Cliente.id == item.clienteId).first()
        if not client:
            raise HTTPException(404, "Cliente não encontrado neste escritório")
        clients[item.clienteId] = client
    db.query(ProcessClient).filter_by(processo_id=process.id, tenant_id=process.tenant_id).delete(synchronize_session=False)
    for item in items:
        client = clients[item.clienteId]
        snapshot = _client_dict(client)
        db.add(ProcessClient(
            id=str(uuid.uuid4()), tenant_id=process.tenant_id, processo_id=process.id,
            cliente_id=client.id, posicao_processual=item.proceduralRole,
            polo_processual=item.proceduralPole, cliente_principal=int(item is primary),
            snapshot_qualificacao=snapshot, observacoes=item.notes,
            criado_por=payload.get("sub"), ativo=1,
        ))
    if primary:
        process.cliente_id = primary.clienteId
    db.commit()
    return [_link_dict(link, clients[link.cliente_id]) for link in db.query(ProcessClient).filter_by(processo_id=process.id, tenant_id=process.tenant_id, ativo=1).all()]


@router.post("/k1/lex/processos/{process_id}/clients")
def save_process_clients(process_id: str, body: Union[ProcessoClientesReplaceIn, ProcessoClienteIn], db: Session = Depends(get_db), payload=Depends(auth_guard)):
    if isinstance(body, ProcessoClientesReplaceIn):
        return _save_links(process_id, body, db, payload)

    existing = list_process_clients(process_id, db, payload)
    items = [ProcessoClienteIn(clienteId=x["id"], proceduralRole=x["proceduralRole"], proceduralPole=x["proceduralPole"], isPrimary=x["isPrimary"], notes=x["notes"]) for x in existing]
    if any(item.clienteId == body.clienteId for item in items):
        raise HTTPException(409, "Cliente já vinculado ao processo")
    if body.isPrimary:
        items = [item.model_copy(update={"isPrimary": False}) for item in items]
    items.append(body)
    return _save_links(process_id, ProcessoClientesReplaceIn(clientes=items), db, payload)


@router.patch("/k1/lex/processos/{process_id}/clients/{client_id}")
def update_process_client(process_id: str, client_id: str, body: ProcessoClienteUpdate, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    links = list_process_clients(process_id, db, payload)
    if not any(row["id"] == client_id for row in links):
        raise HTTPException(404, "Vínculo não encontrado")
    updated = []
    for row in links:
        data = body.model_dump(exclude_none=True) if row["id"] == client_id else {}
        if row["id"] != client_id and body.isPrimary is True:
            data = {"isPrimary": False}
        updated.append(ProcessoClienteIn(
            clienteId=row["id"], proceduralRole=data.get("proceduralRole", row["proceduralRole"]),
            proceduralPole=data.get("proceduralPole", row["proceduralPole"]),
            isPrimary=data.get("isPrimary", row["isPrimary"]), notes=data.get("notes", row["notes"]),
        ))
    return _save_links(process_id, ProcessoClientesReplaceIn(clientes=updated), db, payload)


@router.delete("/k1/lex/processos/{process_id}/clients/{client_id}")
def unlink_process_client(process_id: str, client_id: str, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    links = list_process_clients(process_id, db, payload)
    target = next((row for row in links if row["id"] == client_id), None)
    if not target:
        raise HTTPException(404, "Vínculo não encontrado")
    if target["isPrimary"]:
        raise HTTPException(409, "Defina outro cliente como principal antes de desvincular este cliente")
    kept = [ProcessoClienteIn(clienteId=row["id"], proceduralRole=row["proceduralRole"], proceduralPole=row["proceduralPole"], isPrimary=row["isPrimary"], notes=row["notes"]) for row in links if row["id"] != client_id]
    return _save_links(process_id, ProcessoClientesReplaceIn(clientes=kept), db, payload)


@router.get("/k1/lex/processos/{process_id}/parties")
def list_process_parties(process_id: str, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    process = _scoped_process(db, process_id, payload)
    if not process:
        raise HTTPException(404, "Processo não encontrado")
    parties = db.query(ProcessParty).filter_by(processo_id=process.id, tenant_id=process.tenant_id).all()
    return [{"id": p.id, "name": p.nome, "personType": p.tipo_pessoa, "document": p.documento,
             "email": p.email, "phone": p.telefone, "address": p.endereco,
             "proceduralRole": p.posicao_processual, "isUnknown": bool(p.dados_desconhecidos)} for p in parties]


@router.post("/k1/lex/processos/{process_id}/parties", status_code=201)
def add_process_party(process_id: str, body: ProcessoParteIn, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    process = _scoped_process(db, process_id, payload)
    if not process:
        raise HTTPException(404, "Processo não encontrado")
    if payload.get("role") == "cliente":
        raise HTTPException(403, "Acesso negado")
    party = ProcessParty(id=str(uuid.uuid4()), tenant_id=process.tenant_id, processo_id=process.id,
        nome=body.name, tipo_pessoa=body.personType, documento=body.document, email=body.email,
        telefone=body.phone, endereco=body.address, posicao_processual=body.proceduralRole,
        dados_desconhecidos=int(body.isUnknown), criado_por=payload.get("sub"))
    db.add(party); db.commit(); db.refresh(party)
    return {"id": party.id, "name": party.nome, "personType": party.tipo_pessoa,
            "document": party.documento, "email": party.email, "phone": party.telefone,
            "address": party.endereco, "proceduralRole": party.posicao_processual, "isUnknown": bool(party.dados_desconhecidos)}


@router.put("/k1/lex/processos/{process_id}/parties")
def replace_process_parties(process_id: str, body: ProcessoPartesReplaceIn, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    process = _scoped_process(db, process_id, payload)
    if not process:
        raise HTTPException(404, "Processo não encontrado")
    if payload.get("role") == "cliente":
        raise HTTPException(403, "Acesso negado")
    db.query(ProcessParty).filter_by(processo_id=process.id, tenant_id=process.tenant_id).delete(synchronize_session=False)
    parties = []
    for body_party in body.partes:
        party = ProcessParty(id=str(uuid.uuid4()), tenant_id=process.tenant_id, processo_id=process.id,
            nome=body_party.name, tipo_pessoa=body_party.personType, documento=body_party.document,
            email=body_party.email, telefone=body_party.phone, endereco=body_party.address,
            posicao_processual=body_party.proceduralRole, dados_desconhecidos=int(body_party.isUnknown),
            criado_por=payload.get("sub"))
        db.add(party)
        parties.append(party)
    db.commit()
    return [{"id": p.id, "name": p.nome, "personType": p.tipo_pessoa, "document": p.documento,
             "email": p.email, "phone": p.telefone, "address": p.endereco,
             "proceduralRole": p.posicao_processual, "isUnknown": bool(p.dados_desconhecidos)} for p in parties]
