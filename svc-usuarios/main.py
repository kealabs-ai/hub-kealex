import os, uuid, enum, sys
import json
from datetime import datetime
from typing import Optional
from urllib.error import HTTPError as UrlHTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import bcrypt
from jose import jwt, JWTError
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Enum as SAEnum, ForeignKey, Text as SAText, UniqueConstraint, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, "/app")
try:
    from trial_guard import require_active_trial
except ImportError:
    require_active_trial = None

def _get_database_url():
    host = os.getenv("KEALEX_DB_HOST")
    database = os.getenv("KEALEX_DB_NAME")
    username = os.getenv("KEALEX_DB_USER")
    password = os.getenv("KEALEX_DB_PASSWORD")
    if host and database and username and password is not None:
        return URL.create(
            drivername="mysql+pymysql",
            username=username,
            password=password,
            host=host,
            port=int(os.getenv("KEALEX_DB_PORT", "3306")),
            database=database,
        )
    raw = os.getenv("KEALEX_DATABASE_URL")
    if raw is None or raw.strip().lower() in ("", "null", "none"):
        raise RuntimeError("Configure KEALEX_DB_HOST, KEALEX_DB_NAME, KEALEX_DB_USER e KEALEX_DB_PASSWORD (ou KEALEX_DATABASE_URL)")
    return make_url(raw.strip())

KEALEX_DATABASE_URL = _get_database_url()
KEALEX_SECRET_KEY   = os.getenv("KEALEX_SECRET_KEY") or os.getenv("KEALEX_JWT_SECRET")
if not KEALEX_SECRET_KEY:
    raise RuntimeError("KEALEX_SECRET_KEY ou KEALEX_JWT_SECRET precisa estar configurada no ambiente")
ALGORITHM    = "HS256"

engine       = create_engine(
    KEALEX_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
bearer       = HTTPBearer()

def _hash(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

class Base(DeclarativeBase): pass

class RoleEnum(str, enum.Enum):
    admin    = "admin"
    escritorio = "escritorio"
    advogado = "advogado"
    juridico = "juridico"
    cliente  = "cliente"

class Usuario(Base):
    __tablename__ = "usuarios"
    id           = Column(String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id    = Column(String(36),  nullable=False)
    escritorio_id = Column(String(36), nullable=True)
    codigo = Column(String(16), nullable=True)
    oab = Column(String(50), nullable=True)
    nome         = Column(String(255), nullable=False)
    email        = Column(String(255), nullable=False)
    senha_hash   = Column(String(255), nullable=False)
    role         = Column(SAEnum(RoleEnum, name="role_enum_auth"), nullable=False)
    ativo        = Column(Boolean,     default=True)
    created_at   = Column(DateTime,    default=datetime.utcnow)
    updated_at   = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

class UsuarioChavePublica(Base):
    __tablename__ = "usuarios_chaves_publicas"
    __table_args__ = (UniqueConstraint("user_id", "orgao", name="uq_usuario_chave_publica_orgao"),)
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    orgao = Column(String(120), nullable=False)
    chave_publica = Column(SAText, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        try:
            db.rollback()
        except Exception:
            # Preserve the original request error if MySQL already dropped the connection.
            pass
        raise
    finally:
        db.close()

def verify_token(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return jwt.decode(creds.credentials, KEALEX_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Token inválido")

def require_admin(payload=Depends(verify_token)):
    if payload.get("role") != "admin":
        raise HTTPException(403, "Acesso negado")
    return payload

# admin é sempre isento do trial, mas aplicamos o guard para bloquear
# advogados/clientes que tentem acessar endpoints de usuários com trial expirado
_base_guard = require_active_trial if require_active_trial else verify_token

def _admin_guard(payload=Depends(_base_guard)):
    if payload.get("role") != "admin":
        raise HTTPException(403, "Acesso negado")
    return payload

def _team_guard(payload=Depends(_base_guard)):
    if payload.get("role") not in ("admin", "escritorio"):
        raise HTTPException(403, "Acesso negado")
    if payload.get("role") == "escritorio" and not payload.get("escritorio_id"):
        raise HTTPException(403, "Conta de escritório sem vínculo configurado")
    return payload

app = FastAPI(title="svc-usuarios")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status": "ok", "service": "svc-usuarios"}

class UsuarioIn(BaseModel):
    nome:         str
    email:        EmailStr
    senha:        str
    role:         RoleEnum
    escritorioId: Optional[str] = None
    oab: Optional[str] = None

class UsuarioListIn(BaseModel):
    role: Optional[RoleEnum] = None

class UsuarioGetIn(BaseModel):
    id: str

class UsuarioUpdate(BaseModel):
    id:           str
    nome:         Optional[str]      = None
    email:        Optional[EmailStr] = None
    senha:        Optional[str]      = None
    role:         Optional[RoleEnum] = None
    ativo:        Optional[bool]     = None
    escritorioId: Optional[str]      = None
    clearEscritorio: bool            = False  # True = desassociar escritório

    oab: Optional[str] = None

class UsuarioDeleteIn(BaseModel):
    id: str

class ChavePublicaIn(BaseModel):
    orgao: str
    chavePublica: str

class ConsultaDataJudIn(BaseModel):
    tribunal: str
    numeroProcesso: str

OFFICE_LIMIT_MESSAGE = "Limite de {limit} advogados atingido para este escritório. Entre em contato com o suporte/admin para alterar o limite."


def _ensure_escritorio_capacity(db: Session, tenant_id: str, escritorio_id: str, exclude_user_id: Optional[str] = None):
    office = db.execute(
        text("SELECT limite_advogados FROM escritorios WHERE id = :eid AND tenant_id = :tid FOR UPDATE"),
        {"eid": escritorio_id, "tid": tenant_id},
    ).mappings().first()
    if not office:
        raise HTTPException(404, "Escritório não encontrado")

    query = "SELECT COUNT(*) FROM usuarios WHERE escritorio_id = :eid AND tenant_id = :tid AND ativo = 1 AND role = 'advogado'"
    params = {"eid": escritorio_id, "tid": tenant_id}
    if exclude_user_id:
        query += " AND id <> :uid"
        params["uid"] = exclude_user_id
    count = db.execute(text(query), params).scalar_one()
    limit = int(office["limite_advogados"])
    if count >= limit:
        raise HTTPException(400, OFFICE_LIMIT_MESSAGE.format(limit=limit))


def _to_dict(u: Usuario, db: Session):
    escritorio_nome = None
    if u.escritorio_id:
        escritorio_nome = db.execute(
            text("SELECT nome FROM escritorios WHERE id = :eid AND tenant_id = :tid"),
            {"eid": u.escritorio_id, "tid": u.tenant_id}
        ).scalar_one_or_none()
    return {
        "id": u.id, "tenantId": u.tenant_id, "escritorioId": u.escritorio_id,
        "escritorioNome": escritorio_nome,
        "codigoEscritorio": u.codigo,
        "modalidade": "escritorio" if u.escritorio_id else "autonomo",
        "nome": u.nome, "email": u.email, "role": u.role, "ativo": u.ativo, "oab": getattr(u, "oab", None),
        "createdAt": u.created_at.isoformat(), "updatedAt": u.updated_at.isoformat()
    }

@app.get("/v1/lex/usuarios")
def list_usuarios(db: Session = Depends(get_db), payload=Depends(_team_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    q = db.query(Usuario).filter_by(tenant_id=tenant_id)
    if payload.get("role") == "escritorio":
        q = q.filter_by(escritorio_id=payload.get("escritorio_id"), role=RoleEnum.advogado)
    return [_to_dict(u, db) for u in q.all()]

@app.post("/v1/lex/usuarios/list")
def list_usuarios_filtered(body: UsuarioListIn, db: Session = Depends(get_db), payload=Depends(_team_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    q = db.query(Usuario).filter_by(tenant_id=tenant_id)
    if body.role:
        q = q.filter_by(role=body.role)
    if payload.get("role") == "escritorio":
        q = q.filter_by(escritorio_id=payload.get("escritorio_id"), role=RoleEnum.advogado)
    return [_to_dict(u, db) for u in q.all()]

@app.post("/v1/lex/usuarios/get")
def get_usuario(body: UsuarioGetIn, db: Session = Depends(get_db), payload=Depends(_team_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    u = db.query(Usuario).filter_by(id=body.id, tenant_id=tenant_id).first()
    if payload.get("role") == "escritorio" and (u is None or u.escritorio_id != payload.get("escritorio_id") or u.role != RoleEnum.advogado):
        raise HTTPException(404, "NÃ£o encontrado")
    if not u:
        raise HTTPException(404, "Não encontrado")
    return _to_dict(u, db)

@app.post("/v1/lex/usuarios", status_code=201)
def create_usuario(body: UsuarioIn, db: Session = Depends(get_db), payload=Depends(_team_guard)):
    tid = payload.get("tenant_id") or payload.get("sub")
    escritorio_id = body.escritorioId
    if payload.get("role") == "escritorio":
        escritorio_id = payload.get("escritorio_id")
        if body.role != RoleEnum.advogado:
            raise HTTPException(403, "O escritÃ³rio pode cadastrar apenas advogados associados")
    if body.role == RoleEnum.escritorio:
        raise HTTPException(403, "A conta de escritÃ³rio deve ser criada pelo administrador")
    if escritorio_id:
        _ensure_escritorio_capacity(db, tid, escritorio_id)
        codigo_escritorio = db.execute(
            text("SELECT codigo FROM escritorios WHERE id = :eid AND tenant_id = :tid"),
            {"eid": escritorio_id, "tid": tid},
        ).scalar_one_or_none()
    else:
        codigo_escritorio = None
    if db.query(Usuario).filter_by(email=body.email, tenant_id=tid).first():
        raise HTTPException(409, "Email já cadastrado")
    u = Usuario(tenant_id=tid, escritorio_id=escritorio_id, codigo=codigo_escritorio, nome=body.nome, email=body.email,
                senha_hash=_hash(body.senha), role=body.role)
    if hasattr(u, "oab"):
        u.oab = body.oab
    db.add(u); db.commit(); db.refresh(u)
    return _to_dict(u, db)

@app.post("/v1/lex/usuarios/update")
def update_usuario(body: UsuarioUpdate, db: Session = Depends(get_db), payload=Depends(_team_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    u = db.query(Usuario).filter_by(id=body.id, tenant_id=tenant_id).first()
    if payload.get("role") == "escritorio" and u and (u.escritorio_id != payload.get("escritorio_id") or u.role != RoleEnum.advogado):
        raise HTTPException(404, "UsuÃ¡rio nÃ£o encontrado")
    if payload.get("role") == "escritorio" and (body.role not in (None, RoleEnum.advogado) or body.escritorioId is not None or body.clearEscritorio):
        raise HTTPException(403, "O escritÃ³rio pode editar apenas seus advogados associados")
    if not u:
        raise HTTPException(404, "Não encontrado")
    if body.escritorioId and not db.execute(
        text("SELECT id FROM escritorios WHERE id = :eid AND tenant_id = :tid"),
        {"eid": body.escritorioId, "tid": tenant_id},
    ).first():
        raise HTTPException(404, "Escritório não encontrado")
    target_escritorio_id = body.escritorioId if body.escritorioId is not None else (None if body.clearEscritorio else u.escritorio_id)
    will_be_active = body.ativo if body.ativo is not None else u.ativo
    adding_active_member = bool(
        target_escritorio_id
        and will_be_active
        and (target_escritorio_id != u.escritorio_id or not u.ativo)
    )
    if adding_active_member:
        _ensure_escritorio_capacity(db, tenant_id, target_escritorio_id, exclude_user_id=u.id)
    data = body.model_dump(exclude_none=True, exclude={"id", "clearEscritorio"})
    if "senha" in data:
        u.senha_hash = _hash(data.pop("senha"))
    if "escritorioId" in data:
        u.escritorio_id = data.pop("escritorioId")
        u.codigo = db.execute(
            text("SELECT codigo FROM escritorios WHERE id = :eid"), {"eid": u.escritorio_id}
        ).scalar_one_or_none() if u.escritorio_id else None
    elif body.clearEscritorio:
        u.escritorio_id = None
        u.codigo = None
    for k, v in data.items():
        setattr(u, k, v)
    u.updated_at = datetime.utcnow()
    db.commit(); db.refresh(u)
    return _to_dict(u, db)

class ModalidadeIn(BaseModel):
    usuarioId: str
    escritorioId: Optional[str] = None  # None = autônomo

@app.post("/v1/lex/usuarios/delete")
def delete_usuario(body: UsuarioDeleteIn, db: Session = Depends(get_db), payload=Depends(_admin_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    u = db.query(Usuario).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not u:
        raise HTTPException(404, "Não encontrado")
    db.delete(u); db.commit()
    return {"ok": True}

@app.post("/v1/lex/usuarios/modalidade")
def set_modalidade(body: ModalidadeIn, db: Session = Depends(get_db), payload=Depends(_base_guard)):
    """Admin gerencia membros; advogado pode alterar apenas o próprio vínculo."""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    uid = body.usuarioId
    if payload.get("role") != "admin" and (payload.get("role") != "advogado" or uid != payload.get("sub")):
        raise HTTPException(403, "Você só pode alterar sua própria modalidade")
    u = db.query(Usuario).filter_by(id=uid, tenant_id=tenant_id).first()
    if not u:
        raise HTTPException(404, "Usuário não encontrado")
    if body.escritorioId and not db.execute(
        text("SELECT id FROM escritorios WHERE id = :eid AND tenant_id = :tid"),
        {"eid": body.escritorioId, "tid": tenant_id},
    ).first():
        raise HTTPException(404, "Escritório não encontrado")
    if body.escritorioId and body.escritorioId != u.escritorio_id and u.ativo:
        _ensure_escritorio_capacity(db, tenant_id, body.escritorioId, exclude_user_id=u.id)
    u.escritorio_id = body.escritorioId
    u.codigo = db.execute(
        text("SELECT codigo FROM escritorios WHERE id = :eid"), {"eid": body.escritorioId}
    ).scalar_one_or_none() if body.escritorioId else None
    u.updated_at = datetime.utcnow()
    db.commit(); db.refresh(u)
    return _to_dict(u, db)

def _to_public_key_dict(item: UsuarioChavePublica):
    return {
        "id": item.id,
        "userId": item.user_id,
        "orgao": item.orgao,
        "chavePublica": item.chave_publica,
        "createdAt": item.created_at.isoformat(),
        "updatedAt": item.updated_at.isoformat(),
    }

@app.post("/v1/lex/usuarios/consultas/datajud")
def consultar_processo_datajud(
    body: ConsultaDataJudIn,
    db: Session = Depends(get_db),
    payload=Depends(_base_guard),
):
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id") or user_id
    user = db.query(Usuario.id).filter_by(id=user_id, tenant_id=tenant_id).first()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")

    tribunal = body.tribunal.strip().lower()
    aliases_superiores = {"stj": "stj", "tst": "tst", "tse": "tse", "stm": "stm"}
    aliases_estaduais = {
        "tjac": "tjac", "tjal": "tjal", "tjam": "tjam", "tjap": "tjap", "tjba": "tjba",
        "tjce": "tjce", "tjdft": "tjdft", "tjes": "tjes", "tjgo": "tjgo", "tjma": "tjma",
        "tjmg": "tjmg", "tjms": "tjms", "tjmt": "tjmt", "tjpa": "tjpa", "tjpb": "tjpb",
        "tjpe": "tjpe", "tjpi": "tjpi", "tjpr": "tjpr", "tjrj": "tjrj", "tjrn": "tjrn",
        "tjro": "tjro", "tjrr": "tjrr", "tjrs": "tjrs", "tjsc": "tjsc", "tjse": "tjse",
        "tjsp": "tjsp", "tjto": "tjto",
    }
    aliases_federais = {f"trf{region}": f"trf{region}" for region in range(1, 7)}
    aliases_trabalho = {f"trt{region}": f"trt{region}" for region in range(1, 25)}
    ufs = ("ac", "al", "am", "ap", "ba", "ce", "dft", "es", "go", "ma", "mg", "ms", "mt", "pa", "pb", "pe", "pi", "pr", "rj", "rn", "ro", "rr", "rs", "sc", "se", "sp", "to")
    aliases_eleitorais = {f"tre-{uf}": f"tre-{uf}" for uf in ufs}
    aliases_militares = {alias: alias for alias in ("tjmmg", "tjmrs", "tjmsp")}
    aliases = {**aliases_superiores, **aliases_estaduais, **aliases_federais, **aliases_trabalho, **aliases_eleitorais, **aliases_militares}
    justica = "Justi" + chr(231) + "a"
    orgao_por_ramo = {
        **{alias: "Tribunais Superiores" for alias in aliases_superiores},
        **{alias: f"{justica} Federal" for alias in aliases_federais},
        **{alias: f"{justica} do Trabalho" for alias in aliases_trabalho},
        **{alias: f"{justica} Eleitoral" for alias in aliases_eleitorais},
        **{alias: f"{justica} Militar" for alias in aliases_militares},
        **{alias: f"{justica} Estadual" for alias in aliases_estaduais},
    }
    alias = aliases.get(tribunal)
    if not alias:
        raise HTTPException(422, "Tribunal inválido ou não disponível para consulta.")
    key_orgao = orgao_por_ramo[tribunal]
    numero = "".join(char for char in body.numeroProcesso if char in "0123456789")
    if len(numero) != 20:
        raise HTTPException(422, "Informe o número CNJ completo, com 20 dígitos.")

    key_row = db.query(UsuarioChavePublica).filter_by(
        user_id=user_id,
        orgao=key_orgao,
    ).first()
    if not key_row or not key_row.chave_publica.strip():
        raise HTTPException(400, f"Cadastre a chave pública do DataJud para {key_orgao} no Perfil.")

    api_key = key_row.chave_publica.strip()
    if api_key[:7].lower() == "apikey ":
        api_key = api_key[7:].strip()

    # Release the MySQL transaction before waiting on the external DataJud API.
    db.rollback()

    request_body = json.dumps({
        "query": {"match": {"numeroProcesso": numero}},
        "size": 1,
    }).encode("utf-8")
    request = UrlRequest(
        f"https://api-publica.datajud.cnj.jus.br/api_publica_{alias}/_search",
        data=request_body,
        headers={
            "Authorization": f"APIKey {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=25) as response:
            return json.loads(response.read().decode("utf-8"))
    except UrlHTTPError as exc:
        if exc.code in (401, 403):
            raise HTTPException(502, "O DataJud recusou a chave pública. Confira a chave cadastrada no Perfil.") from exc
        if exc.code == 429:
            raise HTTPException(503, "O DataJud está recebendo muitas consultas. Tente novamente em instantes.") from exc
        raise HTTPException(502, f"O DataJud respondeu com erro ({exc.code}).") from exc
    except (URLError, TimeoutError) as exc:
        raise HTTPException(502, "Não foi possível conectar ao DataJud no momento. Tente novamente em instantes.") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(502, "O DataJud retornou uma resposta inválida.") from exc

@app.get("/v1/lex/usuarios/chaves-publicas")
@app.get("/v1/lex/usuarios/me/chaves-publicas")
def list_my_public_keys(db: Session = Depends(get_db), payload=Depends(_base_guard)):
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id") or user_id
    user = db.query(Usuario.id).filter_by(id=user_id, tenant_id=tenant_id).first()
    if not user:
        raise HTTPException(404, "UsuÃ¡rio nÃ£o encontrado")
    items = db.query(UsuarioChavePublica).filter_by(user_id=user_id).order_by(UsuarioChavePublica.orgao).all()
    return [_to_public_key_dict(item) for item in items]

@app.post("/v1/lex/usuarios/chaves-publicas")
@app.post("/v1/lex/usuarios/me/chaves-publicas")
def save_my_public_key(body: ChavePublicaIn, db: Session = Depends(get_db), payload=Depends(_base_guard)):
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id") or user_id
    user = db.query(Usuario.id).filter_by(id=user_id, tenant_id=tenant_id).first()
    if not user:
        raise HTTPException(404, "UsuÃ¡rio nÃ£o encontrado")
    orgao = body.orgao.strip()
    chave_publica = body.chavePublica.strip()
    if not orgao or len(orgao) > 120:
        raise HTTPException(422, "Informe um Ã³rgÃ£o vÃ¡lido (atÃ© 120 caracteres).")
    if not chave_publica or len(chave_publica) > 10000:
        raise HTTPException(422, "Informe uma chave pÃºblica vÃ¡lida (atÃ© 10.000 caracteres).")
    item = db.query(UsuarioChavePublica).filter_by(user_id=user_id, orgao=orgao).with_for_update().first()
    if item:
        item.chave_publica = chave_publica
        item.updated_at = datetime.utcnow()
    else:
        item = UsuarioChavePublica(user_id=user_id, orgao=orgao, chave_publica=chave_publica)
        db.add(item)
    db.commit()
    db.refresh(item)
    return _to_public_key_dict(item)

@app.post("/v1/lex/usuarios/chaves-publicas/{key_id}")
@app.post("/v1/lex/usuarios/me/chaves-publicas/{key_id}")
def update_my_public_key(key_id: str, body: ChavePublicaIn, db: Session = Depends(get_db), payload=Depends(_base_guard)):
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id") or user_id
    if not db.query(Usuario.id).filter_by(id=user_id, tenant_id=tenant_id).first():
        raise HTTPException(404, "UsuÃ¡rio nÃ£o encontrado")

    item = db.query(UsuarioChavePublica).filter_by(id=key_id, user_id=user_id).first()
    if not item:
        raise HTTPException(404, "Chave pÃºblica nÃ£o encontrada")
    orgao = body.orgao.strip()
    chave_publica = body.chavePublica.strip()
    if not orgao or len(orgao) > 120:
        raise HTTPException(422, "Informe um Ã³rgÃ£o vÃ¡lido (atÃ© 120 caracteres).")
    if not chave_publica or len(chave_publica) > 10000:
        raise HTTPException(422, "Informe uma chave pÃºblica vÃ¡lida (atÃ© 10.000 caracteres).")
    duplicate = db.query(UsuarioChavePublica.id).filter(
        UsuarioChavePublica.user_id == user_id,
        UsuarioChavePublica.orgao == orgao,
        UsuarioChavePublica.id != key_id,
    ).first()
    if duplicate:
        raise HTTPException(409, "JÃ¡ existe uma chave cadastrada para este Ã³rgÃ£o.")
    item.orgao = orgao
    item.chave_publica = chave_publica
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return _to_public_key_dict(item)

@app.delete("/v1/lex/usuarios/chaves-publicas/{key_id}")
@app.delete("/v1/lex/usuarios/me/chaves-publicas/{key_id}")
def delete_my_public_key(key_id: str, db: Session = Depends(get_db), payload=Depends(_base_guard)):
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id") or user_id
    if not db.query(Usuario.id).filter_by(id=user_id, tenant_id=tenant_id).first():
        raise HTTPException(404, "UsuÃ¡rio nÃ£o encontrado")
    item = db.query(UsuarioChavePublica).filter_by(id=key_id, user_id=user_id).first()
    if not item:
        raise HTTPException(404, "Chave pÃºblica nÃ£o encontrada")
    db.delete(item)
    db.commit()
    return {"ok": True}

@app.get("/v1/lex/usuarios/me")
def get_me(db: Session = Depends(get_db), payload=Depends(_base_guard)):
    """Retorna dados do próprio usuário autenticado."""
    uid = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    u = db.query(Usuario).filter_by(id=uid, tenant_id=tenant_id).first()
    if not u:
        raise HTTPException(404, "Não encontrado")
    return _to_dict(u, db)
