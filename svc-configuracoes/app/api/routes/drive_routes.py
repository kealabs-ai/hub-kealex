import json
import os
import re
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text as sql_text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.api.dependencies import require_admin, verify_token
from app.application.use_cases.configuration_support import _get_or_create, _row, _upsert
from app.application.use_cases.ai_catalog import MODELOS_DISPONIVEIS, IA_DEFAULT_MODELS, _validate_model_provider
from app.application.use_cases.ai_policy import _assert_ai_menu, _effective_ai_policy, _json_items, _model_allowed, _plan_key
from app.application.use_cases.user_api_keys import _current_api_key_owner, _decrypt_user_api_key, _encrypt_user_api_key, _user_api_key_json, _validate_user_api_key
from app.infrastructure.database.models.configuration_model import AIPlanPolicy, AIUserPolicy, AITokenUsage, AgenteIA, CfgCdn, CfgDatabase, CfgGeral, CfgIa, CfgIaProvider, CfgNotificacoes, CfgSeguranca, CfgUsuarios, DriveSource, IndexacaoArquivos, UserApiKey
from app.infrastructure.database.session import get_db
from app.api.schemas.drive_schema import DriveSourceCreate, DriveSourceUpdate

router = APIRouter()

def _get_drive_service(service_account_json: str):
    """Cria cliente Google Drive a partir de service account"""
    try:
        creds_dict = json.loads(service_account_json)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        raise HTTPException(400, f"Erro ao criar cliente Drive: {str(e)}")

def _extrair_palavras_chave(nome: str) -> str:
    """Extrai palavras-chave do nome do arquivo"""
    return " ".join([p for p in nome.lower().replace("-", " ").replace("_", " ").split() if len(p) > 2])

def _buscar_arquivos_drive(service, pasta_id: str, tipos: list = None) -> list:
    """Lista arquivos de uma pasta no Drive"""
    if not tipos:
        tipos = ["application/pdf", "application/vnd.google-apps.document", 
                 "application/vnd.google-apps.spreadsheet", "text/plain", "application/msword"]
    
    query = f"'{pasta_id}' in parents and trashed = false"
    mime_query = " or ".join([f"mimeType='{t}'" for t in tipos])
    query += f" and ({mime_query})"
    
    try:
        results = service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name, mimeType, size, webViewLink, modifiedTime)",
            pageSize=100
        ).execute()
        return results.get("files", [])
    except HttpError as e:
        return []



@router.post("/k1/lex/drive-sources", status_code=201)
def criar_drive_source(body: DriveSourceCreate, db: Session = Depends(get_db), payload=Depends(require_admin)):
    """Cria uma nova source de Drive (pasta)"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    
    _get_drive_service(body.service_account)
    
    source = DriveSource(
        tenant_id=tenant_id,
        agente_id=body.agente_id,
        pasta_id=body.pasta_id,
        nome_pasta=body.nome_pasta,
        service_account=body.service_account
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return _row(source)

@router.get("/k1/lex/drive-sources")
def listar_drive_sources(db: Session = Depends(get_db), payload=Depends(require_admin)):
    """Lista todas as drive sources do tenant"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    sources = db.query(DriveSource).filter(DriveSource.tenant_id == tenant_id).all()
    return [{**_row(s)} for s in sources]

@router.put("/k1/lex/drive-sources/{source_id}")
def atualizar_drive_source(source_id: str, body: DriveSourceUpdate, db: Session = Depends(get_db), payload=Depends(require_admin)):
    """Atualiza uma drive source"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    source = db.query(DriveSource).filter(
        DriveSource.id == source_id,
        DriveSource.tenant_id == tenant_id
    ).first()
    
    if not source:
        raise HTTPException(404, "Source nÃ£o encontrada")
    
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(source, field, value)
    
    source.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(source)
    return _row(source)

@router.post("/k1/lex/drive-sources/{source_id}/sincronizar")
def sincronizar_drive_source(source_id: str, db: Session = Depends(get_db), payload=Depends(require_admin)):
    """Sincroniza arquivos de uma drive source"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    source = db.query(DriveSource).filter(
        DriveSource.id == source_id,
        DriveSource.tenant_id == tenant_id
    ).first()
    
    if not source:
        raise HTTPException(404, "Source nÃ£o encontrada")
    
    service = _get_drive_service(source.service_account)
    arquivos = _buscar_arquivos_drive(service, source.pasta_id)
    
    for arquivo in arquivos:
        indexacao = db.query(IndexacaoArquivos).filter(
            IndexacaoArquivos.source_id == source_id,
            IndexacaoArquivos.arquivo_id == arquivo["id"]
        ).first()
        
        if not indexacao:
            indexacao = IndexacaoArquivos(
                tenant_id=tenant_id,
                source_id=source_id,
                arquivo_id=arquivo["id"],
                nome=arquivo["name"],
                tipo=arquivo.get("mimeType", "desconhecido"),
                palavras_chave=_extrair_palavras_chave(arquivo["name"]),
                tamanho_bytes=arquivo.get("size"),
                url=arquivo.get("webViewLink")
            )
            db.add(indexacao)
    
    source.ultima_sync = datetime.utcnow()
    db.commit()
    
    return {
        "message": f"{len(arquivos)} arquivos sincronizados",
        "total": len(arquivos),
        "source_id": source_id
    }

@router.get("/k1/lex/drive-sources/{source_id}/arquivos")
def listar_arquivos_indexados(source_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Lista arquivos indexados de uma source"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    arquivos = db.query(IndexacaoArquivos).filter(
        IndexacaoArquivos.source_id == source_id,
        IndexacaoArquivos.tenant_id == tenant_id
    ).all()
    return [{**_row(a)} for a in arquivos]

@router.get("/k1/lex/agentes/{agente_id}/drive-contexto")
def obter_drive_contexto(agente_id: str, prompt: str = "", db: Session = Depends(get_db), payload=Depends(verify_token)):
    """ObtÃ©m contexto do Drive para enriquecer prompt do agente (busca por palavras-chave)"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    
    agente = db.query(AgenteIA).filter(
        AgenteIA.id == agente_id,
        AgenteIA.tenant_id == tenant_id
    ).first()
    
    if not agente:
        raise HTTPException(404, "Agente nÃ£o encontrado")
    
    palavras_prompt = prompt.lower().split() if prompt else []
    sources = db.query(DriveSource).filter(
        DriveSource.tenant_id == tenant_id,
        DriveSource.agente_id == agente_id,
        DriveSource.ativo == True
    ).all()
    
    contexto_arquivos = []
    for source in sources:
        arquivos = db.query(IndexacaoArquivos).filter(
            IndexacaoArquivos.source_id == source.id
        ).all()
        
        for arquivo in arquivos:
            palavras_arquivo = (arquivo.palavras_chave or "").split()
            match_score = sum(1 for p in palavras_prompt if p in palavras_arquivo)
            
            if match_score > 0 or not palavras_prompt:
                contexto_arquivos.append({
                    "nome": arquivo.nome,
                    "tipo": arquivo.tipo,
                    "url": arquivo.url,
                    "score": match_score,
                    "palavras_chave": arquivo.palavras_chave
                })
    
    contexto_arquivos.sort(key=lambda x: x["score"], reverse=True)
    
    prompt_enriquecido = prompt + "\n\n=== CONTEXTO DO DRIVE ===\nArquivos relevantes:\n"
    prompt_enriquecido += "\n".join([f"- {a['nome']} ({a['tipo']}) - {a['url']}" for a in contexto_arquivos[:10]])
    
    return {
        "arquivos_relevantes": contexto_arquivos[:10],
        "total_encontrado": len(contexto_arquivos),
        "prompt_enriquecido": prompt_enriquecido
    }


