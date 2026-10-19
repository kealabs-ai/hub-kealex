# Development Guidelines — hub-kealex

## Code Quality Standards

### File Organization
- Each service is a **single-file FastAPI app** (`main.py`) — all models, schemas, helpers, and routes in one file
- Section order within a file: imports → config/env → DB setup → models → helpers → Pydantic schemas → app instance → routes
- Use ASCII section dividers for readability:
  ```python
  # ── Config ────────────────────────────────────────────────────────────────────
  # ── Models ───────────────────────────────────────────────────────────────────
  # ── Endpoints ─────────────────────────────────────────────────────────────────
  ```

### Naming Conventions
- **Files/modules**: snake_case (`main.py`, `run_sql_file.py`)
- **DB models**: PascalCase (`Tenant`, `Usuario`, `Processo`)
- **Pydantic schemas**: PascalCase with suffix (`LoginIn`, `AuthUser`, `ProcessoUpdate`, `AssinarOut`)
- **Route functions**: snake_case verbs (`list_processos`, `create_processo`, `update_processo`)
- **Helper functions**: prefixed with `_` (`_hash`, `_verify`, `_make_token`, `_digits`, `_row`)
- **Constants**: UPPER_SNAKE_CASE (`ALGORITHM`, `TRIAL_DAYS`, `TOKEN_EXPIRE_MINUTES`)
- **DB columns**: snake_case (`tenant_id`, `created_at`, `senha_hash`)
- **JSON response keys**: camelCase (`tenantId`, `createdAt`, `accessToken`)
- **Env vars**: `KEALEX_` prefix + UPPER_SNAKE_CASE (`KEALEX_DB_HOST`, `KEALEX_JWT_SECRET`)

### Logging
- Use `logging.info/warning` with `[PREFIX]` tags: `[WEBHOOK]`, `[REGISTER]`, `[INIT]`, `[ERRO]`
- Use `print()` for startup/debug messages (not production logging)
- Format: `logging.info("[TAG] message=%s key=%s", value1, value2)`

---

## Database Patterns

### Connection Setup (used in every service)
```python
def _get_database_url():
    host = os.getenv("KEALEX_DB_HOST")
    database = os.getenv("KEALEX_DB_NAME")
    username = os.getenv("KEALEX_DB_USER")
    password = os.getenv("KEALEX_DB_PASSWORD")
    if host and database and username and password is not None:
        return URL.create(
            drivername="mysql+pymysql",
            username=username, password=password,
            host=host, port=int(os.getenv("KEALEX_DB_PORT", "3306")),
            database=database,
        )
    raw = os.getenv("KEALEX_DATABASE_URL")
    if raw is None or raw.strip().lower() in ("", "null", "none"):
        raise RuntimeError("Configure KEALEX_DB_HOST, ...")
    return make_url(raw.strip())

engine = create_engine(KEALEX_DATABASE_URL, pool_pre_ping=True, pool_recycle=280, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
```

### DB Session Dependency (identical across all services)
```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

### Model Definition Pattern
```python
class MyModel(Base):
    __tablename__ = "my_table"
    id         = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id  = Column(String(36), nullable=False)
    user_id    = Column(String(36), nullable=False)
    # ... domain fields ...
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- All PKs are UUID strings (String(36)), generated with `lambda: str(uuid.uuid4())`
- All tables have `tenant_id` for multi-tenancy isolation
- All tables have `created_at` and `updated_at` timestamps
- Domain tables also include `user_id` and optionally `escritorio_id`
- Use `SAEnum` for enum columns: `Column(SAEnum(MyEnum, name="my_enum_name"))`

### Query Patterns
```python
# Always filter by tenant_id
db.query(Model).filter_by(tenant_id=tenant_id).all()
db.query(Model).filter_by(id=body.id, tenant_id=tenant_id).first()

# Bulk update users when tenant status changes
db.query(Usuario).filter_by(tenant_id=tenant.id).update({"ativo": True})

# Upsert pattern (get or create)
row = db.get(Model, primary_key)
if not row:
    row = Model(...)
    db.add(row)
db.commit()
```

### Serialization Helper
```python
def _row(obj) -> dict:
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    if "updated_at" in d and d["updated_at"]:
        d["updated_at"] = d["updated_at"].isoformat()
    return d
```
Use `_row()` for simple model-to-dict conversion. For complex serialization, define a dedicated `_model_to_dict()` function.

---

## Authentication Patterns

### JWT Setup (identical across all services)
```python
KEALEX_SECRET_KEY = os.getenv("KEALEX_SECRET_KEY") or os.getenv("KEALEX_JWT_SECRET")
if not KEALEX_SECRET_KEY:
    raise RuntimeError("KEALEX_SECRET_KEY ou KEALEX_JWT_SECRET precisa estar configurada")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours

bearer = HTTPBearer()

def _make_token(user: Usuario) -> str:
    exp = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user.id, "role": user.role, "tenant_id": user.tenant_id, "exp": exp},
        KEALEX_SECRET_KEY, ALGORITHM,
    )

def verify_token(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return jwt.decode(creds.credentials, KEALEX_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Token inválido")
```

### Role-Based Access
```python
def _require_admin(payload=Depends(verify_token)):
    if payload.get("role") != "admin":
        raise HTTPException(403, "Acesso negado")
    return payload
```

### Extracting Claims from Token
```python
tenant_id = payload.get("tenant_id")
user_id   = payload.get("sub")
role      = payload.get("role")
```

---

## API Design Patterns

### Routing Convention
The codebase uses a **non-REST POST-heavy** convention:
```
GET    /k1/lex/<resource>          # List all (filtered by tenant)
POST   /k1/lex/<resource>          # Create (status_code=201)
POST   /k1/lex/<resource>/get      # Get single (id in request body)
POST   /k1/lex/<resource>/update   # Update (id + fields in body)
POST   /k1/lex/<resource>/delete   # Delete (id in body)
```

### Dual-Path Registration (legacy compatibility)
```python
@app.get("/v1/lex/cobrancas")
@app.get("/k1/lex/cobrancas")
def list_cobrancas(...):
    ...
```

### Standard Response Patterns
- Success: return dict directly or Pydantic model
- Simple success: `return {"ok": True}`
- Not found: `raise HTTPException(404, "Recurso não encontrado")`
- Validation error: `raise HTTPException(400, "Mensagem de erro")`
- Conflict: `raise HTTPException(409, "Já existe...")`
- Unauthorized: `raise HTTPException(401, "Token inválido")`
- Forbidden: `raise HTTPException(403, "Acesso negado")`

### Health Check Endpoints (required in every service)
```python
@app.get("/health")
def health_simple():
    return {"status": "healthy", "service": "service-name"}

@app.get("/k1/lex/health")
def health():
    return {"status": "ok", "service": "service-name"}
```

---

## FastAPI App Setup Pattern

### Standard App Initialization
```python
app = FastAPI(title="Service Name")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or from env var
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

@app.on_event("startup")
def startup_event():
    _init_db()
```

### CORS from Environment (main app pattern)
```python
cors_allowed_origins = [
    origin.strip()
    for origin in os.getenv("KEALEX_CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(CORSMiddleware, allow_origins=cors_allowed_origins, ...)
```

---

## Pydantic Schema Patterns

### Input/Output Schema Naming
- Input schemas: `ModelNameIn` (e.g., `LoginIn`, `ProcessoIn`)
- Output schemas: `ModelNameOut` or descriptive name (e.g., `AuthUser`, `AssinarOut`)
- Update schemas: `ModelNameUpdate` (e.g., `ProcessoUpdate`, `RepositorioUpdate`)

### Optional Fields for Updates
```python
class ProcessoUpdate(BaseModel):
    id: str
    numero: Optional[str] = None
    titulo: Optional[str] = None
    status: Optional[StatusEnum] = None
```

### Applying Updates
```python
for k, v in body.model_dump(exclude_none=True, exclude={"id"}).items():
    setattr(model_instance, k, v)
model_instance.updated_at = datetime.utcnow()
db.commit()
```

---

## External API Integration (Asaas)

### HTTP Client Pattern
```python
import httpx

headers = {
    "access_token": KEALEX_ASAAS_API_KEY,
    "Content-Type": "application/json",
    "User-Agent": "Kealex/1.0.0",
}

try:
    resp = httpx.post(f"{ASAAS_BASE}/endpoint", json=payload, headers=headers, timeout=15)
    if resp.status_code not in (200, 201):
        raise HTTPException(422, f"Asaas recusou: {resp.json().get('errors', resp.text)}")
    data = resp.json()
except httpx.TimeoutException:
    raise HTTPException(504, "Timeout ao conectar com Asaas")
```

### Webhook Security
```python
import hmac

def _verify_webhook_token(token: str | None) -> bool:
    if not KEALEX_ASAAS_WEBHOOK_TOKEN or not token:
        return False
    return hmac.compare_digest(
        token.encode("utf-8"),
        KEALEX_ASAAS_WEBHOOK_TOKEN.encode("utf-8"),
    )
```
Always use `hmac.compare_digest` for token comparison (timing-attack safe).

### Webhook Idempotency
```python
if db.get(AsaasWebhookEvent, event_id):
    return {"ok": True, "duplicated": True}
db.add(AsaasWebhookEvent(id=event_id, event=event_name))
```

---

## Multi-tenancy Rules

1. **Every query must filter by `tenant_id`** extracted from JWT payload
2. **Never expose data across tenants** — always include `filter_by(tenant_id=tenant_id)`
3. **Tenant activation cascades to users**: when `tenant.ativo` changes, update all users:
   ```python
   db.query(Usuario).filter_by(tenant_id=tenant.id).update({"ativo": True/False})
   ```
4. **Slug uniqueness**: generate unique slugs with counter suffix:
   ```python
   slug = email.split("@")[0].lower().replace(".", "-")[:80]
   base_slug, counter = slug, 1
   while db.query(Tenant).filter_by(slug=slug).first():
       slug = f"{base_slug}-{counter}"; counter += 1
   ```

---

## Utility Patterns

### Phone/Document Digit Extraction
```python
def _digits(value: str | None) -> str | None:
    if value is None: return None
    return "".join(c for c in value if c.isdigit())
```
Always strip non-digits from CPF/CNPJ, phone numbers, postal codes before storing.

### Password Hashing
```python
def _hash(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def _verify(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False
```

### Enum Definition Pattern
```python
class MyEnum(str, enum.Enum):
    value_one = "value_one"
    value_two = "value_two"
```
Always inherit from both `str` and `enum.Enum` for JSON serialization compatibility.

---

## Error Handling

- Wrap external API calls in `try/except httpx.TimeoutException` → 504
- Wrap external API calls in `try/except httpx.RequestError` → 502
- Re-raise `HTTPException` explicitly in broad try/except blocks:
  ```python
  try:
      ...
  except HTTPException:
      raise
  except Exception as e:
      raise HTTPException(500, f"Erro: {str(e)}")
  ```
- Never swallow exceptions silently in production paths

---

## Async vs Sync

- Most endpoints are **synchronous** (`def`, not `async def`)
- Use `async def` only when doing async I/O (file uploads, async HTTP with `httpx.AsyncClient`)
- Webhook handlers that read request body use `async def` with `await request.body()`

---

## Modal Pattern (shared_modal.py)

For endpoints that need UI feedback, use the shared modal pattern:
```python
from shared_modal import criar_modal_sucesso, criar_modal_erro, criar_resposta_modal

# Success
modal = criar_modal_sucesso("Operação realizada com sucesso!")
return criar_resposta_modal(True, "Mensagem", modal, data_dict)

# Error
modal = criar_modal_erro("Mensagem de erro")
return criar_resposta_modal(False, "Erro", modal)
```
Always guard with `if MODAL_DISPONIVEL:` for graceful degradation.

---

## Environment Variable Checklist

Every new service must read and validate these at startup:
- `KEALEX_DB_HOST`, `KEALEX_DB_PORT`, `KEALEX_DB_NAME`, `KEALEX_DB_USER`, `KEALEX_DB_PASSWORD`
- `KEALEX_SECRET_KEY` (or `KEALEX_JWT_SECRET` as fallback)
- Raise `RuntimeError` immediately if required vars are missing — fail fast at startup
