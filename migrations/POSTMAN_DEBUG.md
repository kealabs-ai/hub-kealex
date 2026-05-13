# Postman Collection - Kealex IA Debug

## Passo 1: Login
```
POST http://localhost:8000/auth/login
Content-Type: application/json

{
  "email": "admin@kealex.com",
  "senha": "admin123"
}
```

**Copie o `accessToken` da resposta para usar nos próximos requests**

---

## Passo 2: Testar endpoint /ativa (ANTES de configurar)
```
GET http://localhost:8000/configuracoes/ia/ativa
Authorization: Bearer SEU_TOKEN_AQUI
```

**Resposta esperada agora:**
```json
{
  "tenant_id": "xxx",
  "user_id": "xxx",
  "escritorio_id": null,
  "provider": "cerebras",
  "api_key": null,
  "cerebras_api_key": null,
  "groq_api_key": null,
  "modelo": "llama-3.3-70b",
  "max_tokens": 8192,
  "system_prompt": null,
  "ativo": false,
  "updated_at": "2025-01-15T..."
}
```

**Agora retorna config padrão inativa ao invés de 404!**

---

## Passo 3: Configurar Cerebras (Admin)
```
POST http://localhost:8000/configuracoes/ia
Authorization: Bearer SEU_TOKEN_AQUI
Content-Type: application/json

{
  "provider": "cerebras",
  "cerebras_api_key": "csk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "modelo": "llama-3.3-70b",
  "max_tokens": 8192,
  "ativo": true
}
```

---

## Passo 4: Buscar config ativa (DEPOIS de configurar)
```
GET http://localhost:8000/configuracoes/ia/ativa
Authorization: Bearer SEU_TOKEN_AQUI
```

**Resposta esperada:**
```json
{
  "tenant_id": "xxx",
  "user_id": "xxx",
  "escritorio_id": null,
  "provider": "cerebras",
  "api_key": "csk-xxx",
  "cerebras_api_key": "csk-xxx",
  "groq_api_key": null,
  "modelo": "llama-3.3-70b",
  "max_tokens": 8192,
  "system_prompt": null,
  "ativo": true,
  "updated_at": "2025-01-15T..."
}
```

---

## Passo 5: Buscar config (Admin - endpoint completo)
```
GET http://localhost:8000/configuracoes/ia
Authorization: Bearer SEU_TOKEN_AQUI
```

**Resposta esperada (mesma do passo 4)**

---

## Passo 6: Trocar para Groq
```
POST http://localhost:8000/configuracoes/ia
Authorization: Bearer SEU_TOKEN_AQUI
Content-Type: application/json

{
  "provider": "groq",
  "groq_api_key": "gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "modelo": "llama-3.3-70b-versatile",
  "ativo": true
}
```

---

## Passo 7: Verificar mudança
```
GET http://localhost:8000/configuracoes/ia/ativa
Authorization: Bearer SEU_TOKEN_AQUI
```

**Resposta esperada:**
```json
{
  "tenant_id": "xxx",
  "user_id": "xxx",
  "escritorio_id": null,
  "provider": "groq",
  "api_key": "gsk_xxx",
  "cerebras_api_key": "csk-xxx",
  "groq_api_key": "gsk_xxx",
  "modelo": "llama-3.3-70b-versatile",
  "max_tokens": 8192,
  "system_prompt": null,
  "ativo": true,
  "updated_at": "2025-01-15T..."
}
```

**Note que ambas as chaves ficam salvas!**

---

## Logs do Backend

Ao chamar `/configuracoes/ia/ativa`, você verá no console do backend:

```
[IA Config ATIVA] Buscando config ativa para tenant: xxx
[IA Config ATIVA] Cerebras - API Key: Configurada, Ativo: True
[IA Config ATIVA] Retornando: provider=cerebras, modelo=llama-3.3-70b, ativo=True
```

---

## Troubleshooting

### Erro: "Not authenticated"
- Verifique se o token está correto
- Verifique se o header é: `Authorization: Bearer TOKEN`

### Erro: "Acesso negado"
- O endpoint `/configuracoes/ia` requer role=admin
- O endpoint `/configuracoes/ia/ativa` funciona para qualquer usuário

### Retorna config com ativo=false
- Significa que a config existe mas não está ativa
- Use POST para ativar: `{"ativo": true}`

### api_key retorna null
- Significa que não foi configurada nenhuma chave
- Configure via POST com cerebras_api_key ou groq_api_key
