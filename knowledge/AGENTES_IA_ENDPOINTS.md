# Endpoints de Agentes IA

## 📋 Resumo

Todos os endpoints seguem o padrão do projeto usando apenas **GET** e **POST**.

## 🔗 Endpoints Disponíveis

### 1. Listar Todos os Agentes (Admin)

```http
GET /v1/lex/agentes
Authorization: Bearer {token}
```

**Resposta:**
```json
[
  {
    "id": "uuid",
    "tenant_id": "uuid",
    "escritorio_id": "uuid",
    "nome": "Assistente Trabalhista",
    "descricao": "Especializado em direito do trabalho",
    "provider": "groq",
    "api_key": "gsk-...",
    "modelo": "llama-3.3-70b-versatile",
    "max_tokens": 8192,
    "system_prompt": "Você é um especialista...",
    "ativo": true,
    "publico": true,
    "created_at": "2025-01-20T10:00:00",
    "updated_at": "2025-01-20T10:00:00"
  }
]
```

---

### 2. Listar Agentes Públicos (Todos os usuários)

```http
GET /v1/lex/agentes/publicos
Authorization: Bearer {token}
```

**Resposta:** Igual ao endpoint acima, mas retorna apenas agentes com `ativo=true` e `publico=true`

---

### 3. Buscar Agente Específico

```http
POST /v1/lex/agentes/get
Authorization: Bearer {token}
Content-Type: application/json

{
  "id": "uuid-do-agente"
}
```

**Resposta:**
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "nome": "Assistente Trabalhista",
  ...
}
```

---

### 4. Criar Novo Agente (Admin)

```http
POST /v1/lex/agentes
Authorization: Bearer {token}
Content-Type: application/json

{
  "nome": "Assistente Trabalhista",
  "descricao": "Especializado em direito do trabalho",
  "provider": "groq",
  "api_key": "gsk-xxxxx",
  "modelo": "llama-3.3-70b-versatile",
  "max_tokens": 8192,
  "system_prompt": "Você é um especialista em direito trabalhista...",
  "ativo": true,
  "publico": true
}
```

**Validações:**
- `provider` deve ser `"cerebras"` ou `"groq"`
- API key Cerebras deve começar com `"csk-"`
- API key Groq deve começar com `"gsk-"` ou `"gsk_"`

**Resposta:** Status 201 + dados do agente criado

---

### 5. Atualizar Agente (Admin)

```http
POST /v1/lex/agentes/update
Authorization: Bearer {token}
Content-Type: application/json

{
  "id": "uuid-do-agente",
  "nome": "Novo Nome",
  "ativo": false,
  "publico": false
}
```

**Nota:** Todos os campos são opcionais exceto `id`. Apenas os campos fornecidos serão atualizados.

**Resposta:** Dados atualizados do agente

---

### 6. Deletar Agente (Admin)

```http
POST /v1/lex/agentes/delete
Authorization: Bearer {token}
Content-Type: application/json

{
  "id": "uuid-do-agente"
}
```

**Resposta:**
```json
{
  "ok": true
}
```

---

## 🔐 Controle de Acesso

| Endpoint | Admin | Advogado | Cliente |
|----------|-------|----------|---------|
| GET /agentes | ✅ | ❌ | ❌ |
| GET /agentes/publicos | ✅ | ✅ | ✅ |
| POST /agentes/get | ✅ | ✅* | ✅* |
| POST /agentes | ✅ | ❌ | ❌ |
| POST /agentes/update | ✅ | ❌ | ❌ |
| POST /agentes/delete | ✅ | ❌ | ❌ |

*Usuários não-admin só podem ver agentes com `publico=true`

---

## 📊 Campos da Tabela

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| id | CHAR(36) | ✅ | UUID gerado automaticamente |
| tenant_id | CHAR(36) | ✅ | ID do tenant |
| escritorio_id | CHAR(36) | ❌ | ID do escritório (multi-escritório) |
| nome | VARCHAR(255) | ✅ | Nome do agente |
| descricao | TEXT | ❌ | Descrição do agente |
| provider | VARCHAR(50) | ✅ | `cerebras` ou `groq` |
| api_key | TEXT | ✅ | Chave API do provider |
| modelo | VARCHAR(255) | ✅ | Nome do modelo (ex: llama-3.3-70b) |
| max_tokens | INT | ✅ | Máximo de tokens (padrão: 8192) |
| system_prompt | TEXT | ❌ | Prompt personalizado |
| ativo | TINYINT(1) | ✅ | Se o agente está ativo (padrão: 1) |
| publico | TINYINT(1) | ✅ | Se pode ser usado por clientes (padrão: 1) |
| created_at | TIMESTAMP | ✅ | Data de criação |
| updated_at | TIMESTAMP | ✅ | Data de atualização |

---

## 🎯 Exemplos de Uso

### Criar agente Cerebras

```bash
curl -X POST https://api.kealex.com.br/v1/lex/agentes \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Assistente Civil",
    "descricao": "Especialista em direito civil",
    "provider": "cerebras",
    "api_key": "csk-xxxxx",
    "modelo": "llama-3.3-70b",
    "max_tokens": 8192,
    "ativo": true,
    "publico": true
  }'
```

### Criar agente Groq

```bash
curl -X POST https://api.kealex.com.br/v1/lex/agentes \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Assistente Penal",
    "descricao": "Especialista em direito penal",
    "provider": "groq",
    "api_key": "gsk-xxxxx",
    "modelo": "llama-3.3-70b-versatile",
    "max_tokens": 8192,
    "ativo": true,
    "publico": false
  }'
```

---

## 🚀 Testando no Postman

1. Importe a collection `Kealex-Agentes-IA.postman_collection.json`
2. Configure o environment com o token de admin
3. Execute os requests em ordem:
   - Login → Criar Agente → Listar Agentes → Atualizar → Deletar
