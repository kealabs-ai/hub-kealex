import os, uuid, enum
from datetime import datetime
from typing import Optional
import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from sqlalchemy import create_engine, Column, String, DateTime, Enum as SAEnum, Text, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker, relationship

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def _get_database_url(default: str) -> str:
    raw = os.getenv("DATABASE_URL")
    if raw is None or raw.strip().lower() in ("", "null", "none"):
        return default
    return raw.strip()

DATABASE_URL = _get_database_url(
    "mysql+pymysql://u549746795_kealex:Sally2026%40%21%40@srv1078.hstgr.io:3306/u549746795_kealex"
)
SECRET_KEY   = os.getenv("SECRET_KEY", "changeme-secret-key")
ALGORITHM    = "HS256"

engine       = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
bearer       = HTTPBearer()

class Base(DeclarativeBase): pass

class Cliente(Base):
    __tablename__ = "clientes"
    id          = Column(String(36),  primary_key=True)
    tenant_id   = Column(String(36),  nullable=False)
    advogado_id = Column(String(36),  nullable=False)
    nome        = Column(String(255), nullable=False)
    email       = Column(String(255), nullable=False)
    telefone    = Column(String(50),  nullable=True)
    cpf_cnpj    = Column(String(20),  nullable=True)
    endereco    = Column(String(500), nullable=True)
    observacoes = Column(Text,        nullable=True)
    created_at  = Column(DateTime,    default=datetime.utcnow)
    updated_at  = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

class StatusEnum(str, enum.Enum):
    ativo     = "ativo"
    arquivado = "arquivado"
    encerrado = "encerrado"

class Processo(Base):
    __tablename__ = "processos"
    id            = Column(String(36),   primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id     = Column(String(36),   nullable=False)
    user_id       = Column(String(36),   nullable=False)
    escritorio_id = Column(String(36),   nullable=True)
    numero        = Column(String(100),  nullable=False)
    titulo        = Column(String(255),  nullable=False)
    descricao     = Column(String(1000), default="")
    status        = Column(SAEnum(StatusEnum, name="status_processo_enum"), default=StatusEnum.ativo)
    advogado_id   = Column(String(36),   nullable=False)
    cliente_id    = Column(String(36),   nullable=False)
    vara          = Column(String(255),  default="")
    tribunal      = Column(String(255),  default="")
    fase_atual    = Column(Integer,      default=0)
    created_at    = Column(DateTime,     default=datetime.utcnow)
    updated_at    = Column(DateTime,     default=datetime.utcnow, onupdate=datetime.utcnow)
    fases         = relationship("Fase", back_populates="processo", cascade="all, delete-orphan")

class Fase(Base):
    __tablename__ = "fases"
    id            = Column(String(36),   primary_key=True, default=lambda: str(uuid.uuid4()))
    processo_id   = Column(String(36),   ForeignKey("processos.id"), nullable=False)
    label         = Column(String(255),  nullable=False)
    ordem         = Column(Integer,      nullable=False)
    status        = Column(String(50),   default="futura")
    data_conclusao = Column(DateTime,    nullable=True)
    created_at    = Column(DateTime,     default=datetime.utcnow)
    updated_at    = Column(DateTime,     default=datetime.utcnow, onupdate=datetime.utcnow)
    processo      = relationship("Processo", back_populates="fases")

Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def verify_token(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Token invalido")

app = FastAPI(title="svc-processos")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status": "healthy", "service": "svc-processos"}

class ProcessoIn(BaseModel):
    numero:       str
    titulo:       str
    descricao:    str = ""
    clienteId:    str
    vara:         str = ""
    tribunal:     str = ""
    escritorioId: Optional[str] = None

class ProcessoGetIn(BaseModel):
    id: str

class ProcessoUpdate(BaseModel):
    id:        str
    numero:    Optional[str]        = None
    titulo:    Optional[str]        = None
    descricao: Optional[str]        = None
    status:    Optional[StatusEnum] = None
    vara:      Optional[str]        = None
    tribunal:  Optional[str]        = None

class ProcessoDeleteIn(BaseModel):
    id: str

class FaseIn(BaseModel):
    label: str
    ordem: int

class AvancarFaseIn(BaseModel):
    processoId: str
    faseAtual: int

def _to_dict(p: Processo, cliente: Cliente = None):
    fases = sorted(p.fases, key=lambda f: f.ordem) if p.fases else []
    return {
        "id": p.id, "tenantId": p.tenant_id, "userId": p.user_id, "escritorioId": p.escritorio_id,
        "numero": p.numero, "titulo": p.titulo, "descricao": p.descricao, "status": p.status,
        "advogadoId": p.advogado_id, "clienteId": p.cliente_id,
        "clienteNome": cliente.nome if cliente else None,
        "clienteEmail": cliente.email if cliente else None,
        "vara": p.vara, "tribunal": p.tribunal,
        "faseAtual": p.fase_atual,
        "fases": [
            {"id": f.id, "label": f.label, "status": f.status, "data": f.data_conclusao.isoformat() if f.data_conclusao else None}
            for f in fases
        ],
        "createdAt": p.created_at.isoformat(), "updatedAt": p.updated_at.isoformat()
    }

def _enrich(db: Session, processos: list[Processo]):
    ids = list({p.cliente_id for p in processos})
    clientes = {c.id: c for c in db.query(Cliente).filter(Cliente.id.in_(ids)).all()}
    return [_to_dict(p, clientes.get(p.cliente_id)) for p in processos]

@app.get("/k1/lex/processos")
def list_processos(db: Session = Depends(get_db), payload=Depends(verify_token)):
    role, uid, tid = payload.get("role"), payload.get("sub"), payload.get("tenant_id")
    q = db.query(Processo).filter_by(tenant_id=tid)
    
    if role == "cliente":
        q = q.filter_by(cliente_id=uid)
    elif role == "advogado":
        q = q.filter_by(advogado_id=uid)
    
    return _enrich(db, q.all())

@app.post("/k1/lex/processos/get")
def get_processo(body: ProcessoGetIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    p = db.query(Processo).filter_by(id=body.processoId, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Nao encontrado")
    cliente = db.query(Cliente).filter_by(id=p.cliente_id).first()
    return _to_dict(p, cliente)

@app.post("/k1/lex/processos", status_code=201)
def create_processo(body: ProcessoIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    try:
        logger.info(f"[CREATE_PROCESSO] Iniciando criacao de processo: {body.numero}")
        tenant_id = payload.get("tenant_id")
        logger.info(f"[CREATE_PROCESSO] Tenant ID: {tenant_id}")
        
        cliente = db.query(Cliente).filter_by(id=body.clienteId, tenant_id=tenant_id).first()
        if not cliente:
            logger.error(f"[CREATE_PROCESSO] Cliente nao encontrado: {body.clienteId}")
            raise HTTPException(404, "Cliente nao encontrado")
        logger.info(f"[CREATE_PROCESSO] Cliente encontrado: {cliente.nome}")
        
        processo_id = str(uuid.uuid4())
        logger.info(f"[CREATE_PROCESSO] Novo ID do processo: {processo_id}")
        
        p = Processo(
            id=processo_id,
            tenant_id=tenant_id,
            user_id=payload["sub"],
            escritorio_id=body.escritorioId,
            numero=body.numero,
            titulo=body.titulo,
            descricao=body.descricao,
            status=StatusEnum.ativo,
            advogado_id=payload["sub"],
            cliente_id=body.clienteId,
            vara=body.vara,
            tribunal=body.tribunal,
            fase_atual=0
        )
        db.add(p)
        db.commit()
        logger.info(f"[CREATE_PROCESSO] Processo criado com sucesso: {processo_id}")
        
        fases_padrao = [
            Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Protocolo", ordem=0, status="ativa"),
            Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Citacao", ordem=1, status="futura"),
            Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Contestacao", ordem=2, status="futura"),
            Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Audiencia", ordem=3, status="futura"),
            Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Sentenca", ordem=4, status="futura"),
            Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Recurso", ordem=5, status="futura"),
            Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Encerrado", ordem=6, status="futura"),
        ]
        logger.info(f"[CREATE_PROCESSO] Criando {len(fases_padrao)} fases para o processo {processo_id}")
        
        for i, fase in enumerate(fases_padrao):
            logger.debug(f"[CREATE_PROCESSO] Adicionando fase {i}: {fase.label} (ID: {fase.id}, processo_id: {fase.processo_id})")
            db.add(fase)
        
        logger.info(f"[CREATE_PROCESSO] Fazendo commit das fases...")
        db.commit()
        logger.info(f"[CREATE_PROCESSO] Fases criadas com sucesso")
        
        db.refresh(p)
        logger.info(f"[CREATE_PROCESSO] Processo atualizado recuperado do banco")
        
        fases_verificacao = db.query(Fase).filter_by(processo_id=p.id).all()
        logger.info(f"[CREATE_PROCESSO] Verificacao: {len(fases_verificacao)} fases encontradas no banco")
        for fv in fases_verificacao:
            logger.debug(f"[CREATE_PROCESSO] Fase encontrada: {fv.label} (ID: {fv.id}, status: {fv.status})")
        
        resultado = _to_dict(p, cliente)
        logger.info(f"[CREATE_PROCESSO] Processo criado com sucesso com {len(resultado.get('fases', []))} fases")
        return resultado
        
    except Exception as e:
        logger.error(f"[CREATE_PROCESSO] ERRO: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(500, f"Erro ao criar processo: {str(e)}")

@app.post("/k1/lex/processos/update")
def update_processo(body: ProcessoUpdate, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    p = db.query(Processo).filter_by(id=body.processoId, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Nao encontrado")
    for k, v in body.model_dump(exclude_none=True, exclude={"id"}).items():
        setattr(p, k, v)
    p.updated_at = datetime.utcnow()
    db.commit(); db.refresh(p)
    cliente = db.query(Cliente).filter_by(id=p.cliente_id).first()
    return _to_dict(p, cliente)

@app.post("/k1/lex/processos/delete")
def delete_processo(body: ProcessoDeleteIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    p = db.query(Processo).filter_by(id=body.processoId, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Nao encontrado")
    db.delete(p); db.commit()
    return {"ok": True}

@app.post("/k1/lex/processos/avancar-fase")
def avancar_fase(body: AvancarFaseIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    try:
        logger.info(f"[AVANCAR_FASE] Iniciando avanco de fase para processo: {body.processoId}, nova fase: {body.faseAtual}")
        tenant_id = payload.get("tenant_id")
        
        p = db.query(Processo).filter_by(id=body.processoId, tenant_id=tenant_id).first()
        if not p:
            logger.error(f"[AVANCAR_FASE] Processo nao encontrado: {body.processoId}")
            raise HTTPException(404, "Processo nao encontrado")
        logger.info(f"[AVANCAR_FASE] Processo encontrado: {p.numero}")
        
        fases = db.query(Fase).filter_by(processo_id=p.id).order_by(Fase.ordem).all()
        logger.info(f"[AVANCAR_FASE] Total de fases encontradas: {len(fases)}")
        
        if not fases:
            logger.error(f"[AVANCAR_FASE] Nenhuma fase encontrada para o processo {body.processoId}")
            raise HTTPException(400, "Nenhuma fase encontrada para este processo")
        
        if body.faseAtual < 0 or body.faseAtual >= len(fases):
            logger.error(f"[AVANCAR_FASE] Fase invalida: {body.faseAtual}. Maximo: {len(fases) - 1}")
            raise HTTPException(400, f"Nenhuma próxima fase disponível")
        
        logger.info(f"[AVANCAR_FASE] Atualizando status das fases...")
        for i, fase in enumerate(fases):
            if i < body.faseAtual:
                fase.status = "concluida"
                if not fase.data_conclusao:
                    fase.data_conclusao = datetime.utcnow()
                logger.debug(f"[AVANCAR_FASE] Fase {i} ({fase.label}) marcada como concluida")
            elif i == body.faseAtual:
                fase.status = "ativa"
                logger.debug(f"[AVANCAR_FASE] Fase {i} ({fase.label}) marcada como ativa")
            else:
                fase.status = "futura"
                logger.debug(f"[AVANCAR_FASE] Fase {i} ({fase.label}) marcada como futura")
            db.add(fase)
        
        p.fase_atual = body.faseAtual
        p.updated_at = datetime.utcnow()
        db.add(p)
        logger.info(f"[AVANCAR_FASE] Fazendo commit das mudancas...")
        db.commit()
        logger.info(f"[AVANCAR_FASE] Avanco de fase realizado com sucesso")
        
        p_atualizado = db.query(Processo).filter_by(id=p.id).first()
        cliente = db.query(Cliente).filter_by(id=p_atualizado.cliente_id).first()
        return _to_dict(p_atualizado, cliente)
        
    except Exception as e:
        logger.error(f"[AVANCAR_FASE] ERRO: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(500, f"Erro ao avancar fase: {str(e)}")
@app.post("/k1/lex/processos/{processo_id}/proximas-fases")
def proximas_fases(processo_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    p = db.query(Processo).filter_by(id=processo_id, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Processo nao encontrado")
    
    fases = db.query(Fase).filter_by(processo_id=processo_id).order_by(Fase.ordem).all()
    fase_atual = p.fase_atual
    
    proximas = []
    for i, fase in enumerate(fases):
        if i > fase_atual:
            proximas.append({
                "ordem": i,
                "label": fase.label,
                "status": fase.status
            })
    
    return {
        "faseAtual": fase_atual,
        "faseAtualLabel": fases[fase_atual].label if fase_atual < len(fases) else None,
        "proximasFases": proximas
    }

@app.get("/k1/lex/processos/{processo_id}/debug-fases")
def debug_fases(processo_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    logger.info(f"[DEBUG_FASES] Verificando fases do processo: {processo_id}")
    tenant_id = payload.get("tenant_id")
    
    p = db.query(Processo).filter_by(id=processo_id, tenant_id=tenant_id).first()
    if not p:
        logger.error(f"[DEBUG_FASES] Processo nao encontrado: {processo_id}")
        raise HTTPException(404, "Processo nao encontrado")
    
    logger.info(f"[DEBUG_FASES] Processo encontrado: {p.numero}")
    
    fases = db.query(Fase).filter_by(processo_id=processo_id).order_by(Fase.ordem).all()
    logger.info(f"[DEBUG_FASES] Total de fases encontradas: {len(fases)}")
    
    fases_info = []
    for f in fases:
        info = {
            "id": f.id,
            "processo_id": f.processo_id,
            "label": f.label,
            "ordem": f.ordem,
            "status": f.status,
            "data_conclusao": f.data_conclusao.isoformat() if f.data_conclusao else None,
            "created_at": f.created_at.isoformat(),
            "updated_at": f.updated_at.isoformat()
        }
        fases_info.append(info)
        logger.debug(f"[DEBUG_FASES] Fase: {info}")
    
    return {
        "processo_id": processo_id,
        "processo_numero": p.numero,
        "fase_atual": p.fase_atual,
        "total_fases": len(fases),
        "fases": fases_info
    }

@app.get("/k1/lex/debug/todas-fases")
def debug_todas_fases(db: Session = Depends(get_db), payload=Depends(verify_token)):
    logger.info(f"[DEBUG_TODAS_FASES] Verificando TODAS as fases do banco")
    
    todas_fases = db.query(Fase).all()
    logger.info(f"[DEBUG_TODAS_FASES] Total de fases no banco: {len(todas_fases)}")
    
    fases_info = []
    for f in todas_fases:
        info = {
            "id": f.id,
            "processo_id": f.processo_id,
            "label": f.label,
            "ordem": f.ordem,
            "status": f.status,
            "created_at": f.created_at.isoformat()
        }
        fases_info.append(info)
        logger.debug(f"[DEBUG_TODAS_FASES] Fase: {info}")
    
    return {
        "total_fases": len(todas_fases),
        "fases": fases_info
    }

@app.get("/k1/lex/debug/todos-processos")
def debug_todos_processos(db: Session = Depends(get_db), payload=Depends(verify_token)):
    logger.info(f"[DEBUG_TODOS_PROCESSOS] Verificando TODOS os processos do banco")
    tenant_id = payload.get("tenant_id")
    
    todos_processos = db.query(Processo).filter_by(tenant_id=tenant_id).all()
    logger.info(f"[DEBUG_TODOS_PROCESSOS] Total de processos encontrados: {len(todos_processos)}")
    
    processos_info = []
    for p in todos_processos:
        fases_count = db.query(Fase).filter_by(processo_id=p.id).count()
        info = {
            "id": p.id,
            "numero": p.numero,
            "titulo": p.titulo,
            "status": p.status,
            "fase_atual": p.fase_atual,
            "total_fases_no_banco": fases_count,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat()
        }
        processos_info.append(info)
        logger.info(f"[DEBUG_TODOS_PROCESSOS] Processo: {p.numero} - Fases no banco: {fases_count}")
    
    return {
        "tenant_id": tenant_id,
        "total_processos": len(todos_processos),
        "processos": processos_info
    }

@app.get("/k1/lex/debug/status-completo")
def debug_status_completo(db: Session = Depends(get_db), payload=Depends(verify_token)):
    logger.info(f"[DEBUG_STATUS_COMPLETO] Iniciando verificacao completa do sistema")
    tenant_id = payload.get("tenant_id")
    
    total_processos = db.query(Processo).filter_by(tenant_id=tenant_id).count()
    total_fases = db.query(Fase).count()
    total_clientes = db.query(Cliente).filter_by(tenant_id=tenant_id).count()
    
    logger.info(f"[DEBUG_STATUS_COMPLETO] Total de processos: {total_processos}")
    logger.info(f"[DEBUG_STATUS_COMPLETO] Total de fases: {total_fases}")
    logger.info(f"[DEBUG_STATUS_COMPLETO] Total de clientes: {total_clientes}")
    
    processos_sem_fases = []
    processos_com_fases = []
    
    todos_processos = db.query(Processo).filter_by(tenant_id=tenant_id).all()
    for p in todos_processos:
        fases_count = db.query(Fase).filter_by(processo_id=p.id).count()
        if fases_count == 0:
            processos_sem_fases.append({
                "id": p.id,
                "numero": p.numero,
                "titulo": p.titulo
            })
            logger.warning(f"[DEBUG_STATUS_COMPLETO] ALERTA: Processo {p.numero} SEM fases!")
        else:
            processos_com_fases.append({
                "id": p.id,
                "numero": p.numero,
                "titulo": p.titulo,
                "fases": fases_count
            })
            logger.info(f"[DEBUG_STATUS_COMPLETO] Processo {p.numero} com {fases_count} fases")
    
    return {
        "tenant_id": tenant_id,
        "resumo": {
            "total_processos": total_processos,
            "total_fases": total_fases,
            "total_clientes": total_clientes,
            "processos_com_fases": len(processos_com_fases),
            "processos_sem_fases": len(processos_sem_fases)
        },
        "processos_com_fases": processos_com_fases,
        "processos_sem_fases": processos_sem_fases
    }
