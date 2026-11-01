from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api.dependencies import auth_guard
from app.api.schemas.document_schema import DocumentoIn, DocumentoGetIn, DocumentoByProcessoIn, DocumentoUpdate, DocumentoDeleteIn
from app.application.use_cases.document_presenter import _to_dict
from app.infrastructure.database.models.document_model import Documento
from app.infrastructure.database.session import get_db
router = APIRouter()

@router.get("/v1/lex/documentos")
def list_docs(db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    return [_to_dict(d) for d in db.query(Documento).filter_by(tenant_id=tenant_id).all()]

@router.post("/v1/lex/documentos/get")
def get_doc(body: DocumentoGetIn, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    d = db.query(Documento).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not d:
        raise HTTPException(404, "Não encontrado")
    return _to_dict(d)

@router.post("/v1/lex/documentos/by-processo")
def by_processo(body: DocumentoByProcessoIn, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    return [_to_dict(d) for d in db.query(Documento).filter_by(
        tenant_id=tenant_id, processo_id=body.processoId).all()]

@router.post("/v1/lex/documentos", status_code=201)
def create_doc(body: DocumentoIn, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    processo = db.execute(
        text("SELECT id, escritorio_id FROM processos WHERE id = :pid AND tenant_id = :tid"),
        {"pid": body.processoId, "tid": tenant_id},
    ).first()
    if not processo:
        raise HTTPException(404, "Processo não encontrado")
    d = Documento(tenant_id=tenant_id, user_id=payload["sub"], escritorio_id=processo.escritorio_id,
                  processo_id=body.processoId, uploadado_por_id=payload["sub"], nome=body.nome, tipo=body.tipo,
                  url_arquivo=body.urlArquivo, tamanho_bytes=body.tamanhoBytes)
    db.add(d); db.commit(); db.refresh(d)
    return _to_dict(d)

@router.post("/v1/lex/documentos/update")
def update_doc(body: DocumentoUpdate, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    d = db.query(Documento).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not d:
        raise HTTPException(404, "Não encontrado")
    data = body.model_dump(exclude_none=True, exclude={"id"})
    if "urlArquivo" in data:
        d.url_arquivo = data.pop("urlArquivo")
    for k, v in data.items():
        setattr(d, k, v)
    d.updated_at = datetime.utcnow()
    db.commit(); db.refresh(d)
    return _to_dict(d)

@router.post("/v1/lex/documentos/delete")
def delete_doc(body: DocumentoDeleteIn, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    d = db.query(Documento).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not d:
        raise HTTPException(404, "Não encontrado")
    db.delete(d); db.commit()
    return {"ok": True}


