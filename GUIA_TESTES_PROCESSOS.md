# 🧪 Guia de Testes - Endpoints de Processos

## Pré-requisitos

1. Backend rodando em `http://localhost:8000`
2. Token JWT válido (obter via login)
3. Cliente existente no banco de dados
4. Postman ou similar para testar

## 1️⃣ Obter Token JWT

**POST** `http://localhost:8000/auth/login`

```json
{
  "email": "adv@keahub.com",
  "senha": "adv123"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

Copiar o `access_token` para usar nos próximos testes.

---

## 2️⃣ Criar Processo (com Fases Padrão)

**POST** `http://localhost:8000/k1/lex/processos`

**Headers:**
```
Authorization: Bearer {seu-token-aqui}
Content-Type: application/json
```

**Body:**
```json
{
  "numero": "0001234-56.2024.8.26.0100",
  "titulo": "Ação Civil - Cobrança",
  "descricao": "Processo de cobrança de débito",
  "clienteId": "cliente-uuid-aqui",
  "vara": "1ª Vara Cível",
  "tribunal": "TJSP",
  "escritorioId": null
}
```

**Response (201 Created):**
```json
{
  "id": "processo-uuid",
  "numero": "0001234-56.2024.8.26.0100",
  "titulo": "Ação Civil - Cobrança",
  "status": "ativo",
  "faseAtual": 0,
  "fases": [
    {
      "id": "fase-uuid-1",
      "label": "Protocolo",
      "status": "ativa",
      "data": null
    },
    {
      "id": "fase-uuid-2",
      "label": "Citação",
      "status": "futura",
      "data": null
    },
    {
      "id": "fase-uuid-3",
      "label": "Contestação",
      "status": "futura",
      "data": null
    },
    {
      "id": "fase-uuid-4",
      "label": "Sentença",
      "status": "futura",
      "data": null
    },
    {
      "id": "fase-uuid-5",
      "label": "Recurso",
      "status": "futura",
      "data": null
    },
    {
      "id": "fase-uuid-6",
      "label": "Encerrado",
      "status": "futura",
      "data": null
    }
  ],
  "createdAt": "2024-01-15T10:30:00",
  "updatedAt": "2024-01-15T10:30:00"
}
```

**Salvar o `id` do processo para os próximos testes!**

---

## 3️⃣ Listar Processos

**GET** `http://localhost:8000/k1/lex/processos`

**Headers:**
```
Authorization: Bearer {seu-token-aqui}
```

**Response (200 OK):**
```json
[
  {
    "id": "processo-uuid",
    "numero": "0001234-56.2024.8.26.0100",
    "titulo": "Ação Civil - Cobrança",
    "status": "ativo",
    "faseAtual": 0,
    "fases": [
      {
        "id": "fase-uuid-1",
        "label": "Protocolo",
        "status": "ativa",
        "data": null
      },
      ...
    ],
    "createdAt": "2024-01-15T10:30:00",
    "updatedAt": "2024-01-15T10:30:00"
  }
]
```

---

## 4️⃣ Obter Processo Específico

**POST** `http://localhost:8000/k1/lex/processos/get`

**Headers:**
```
Authorization: Bearer {seu-token-aqui}
Content-Type: application/json
```

**Body:**
```json
{
  "id": "processo-uuid-aqui"
}
```

**Response (200 OK):**
```json
{
  "id": "processo-uuid",
  "numero": "0001234-56.2024.8.26.0100",
  "titulo": "Ação Civil - Cobrança",
  "status": "ativo",
  "faseAtual": 0,
  "fases": [
    {
      "id": "fase-uuid-1",
      "label": "Protocolo",
      "status": "ativa",
      "data": null
    },
    ...
  ],
  "createdAt": "2024-01-15T10:30:00",
  "updatedAt": "2024-01-15T10:30:00"
}
```

---

## 5️⃣ Avançar Fase ⭐ (NOVO)

**POST** `http://localhost:8000/k1/lex/processos/avancar-fase`

**Headers:**
```
Authorization: Bearer {seu-token-aqui}
Content-Type: application/json
```

**Body:**
```json
{
  "id": "processo-uuid-aqui",
  "novaFase": 1
}
```

**Response (200 OK):**
```json
{
  "id": "processo-uuid",
  "numero": "0001234-56.2024.8.26.0100",
  "titulo": "Ação Civil - Cobrança",
  "status": "ativo",
  "faseAtual": 1,
  "fases": [
    {
      "id": "fase-uuid-1",
      "label": "Protocolo",
      "status": "concluida",
      "data": "2024-01-15T10:35:00"
    },
    {
      "id": "fase-uuid-2",
      "label": "Citação",
      "status": "ativa",
      "data": null
    },
    {
      "id": "fase-uuid-3",
      "label": "Contestação",
      "status": "futura",
      "data": null
    },
    ...
  ],
  "createdAt": "2024-01-15T10:30:00",
  "updatedAt": "2024-01-15T10:35:00"
}
```

**Observações:**
- `faseAtual` mudou de 0 para 1
- Fase anterior (Protocolo) agora tem `status: "concluida"` e `data` preenchida
- Fase atual (Citação) agora tem `status: "ativa"`
- Fases futuras mantêm `status: "futura"`

---

## 6️⃣ Atualizar Processo

**POST** `http://localhost:8000/k1/lex/processos/update`

**Headers:**
```
Authorization: Bearer {seu-token-aqui}
Content-Type: application/json
```

**Body:**
```json
{
  "id": "processo-uuid-aqui",
  "titulo": "Ação Civil - Cobrança (Atualizado)",
  "descricao": "Descrição atualizada",
  "status": "ativo"
}
```

**Response (200 OK):**
```json
{
  "id": "processo-uuid",
  "numero": "0001234-56.2024.8.26.0100",
  "titulo": "Ação Civil - Cobrança (Atualizado)",
  "descricao": "Descrição atualizada",
  "status": "ativo",
  "faseAtual": 1,
  "fases": [...],
  "createdAt": "2024-01-15T10:30:00",
  "updatedAt": "2024-01-15T10:40:00"
}
```

---

## 7️⃣ Deletar Processo

**POST** `http://localhost:8000/k1/lex/processos/delete`

**Headers:**
```
Authorization: Bearer {seu-token-aqui}
Content-Type: application/json
```

**Body:**
```json
{
  "id": "processo-uuid-aqui"
}
```

**Response (200 OK):**
```json
{
  "ok": true
}
```

---

## 📊 Fluxo Completo de Teste

1. ✅ Fazer login e obter token
2. ✅ Criar novo processo (salvar ID)
3. ✅ Listar processos
4. ✅ Obter processo específico
5. ✅ Avançar fase (1ª vez)
6. ✅ Avançar fase (2ª vez)
7. ✅ Atualizar processo
8. ✅ Deletar processo

---

## 🔍 Validações Esperadas

| Cenário | Esperado | Status |
|---------|----------|--------|
| Criar processo sem cliente | 404 - Cliente não encontrado | ✅ |
| Avançar fase inválida | 400 - Fase inválida | ✅ |
| Acessar processo de outro tenant | 404 - Não encontrado | ✅ |
| Cliente vê apenas seus processos | Filtrado por cliente_id | ✅ |
| Advogado vê apenas seus processos | Filtrado por advogado_id | ✅ |
| Admin vê todos do tenant | Sem filtro adicional | ✅ |

---

## 🐛 Troubleshooting

### Erro 401 - Token inválido
- Verificar se o token está correto
- Verificar se o token não expirou
- Fazer login novamente

### Erro 404 - Cliente não encontrado
- Verificar se o `clienteId` existe no banco
- Verificar se o cliente pertence ao mesmo tenant

### Erro 400 - Fase inválida
- Verificar se `novaFase` está entre 0 e 5
- Não é possível pular fases

### Erro 500 - Erro interno
- Verificar logs do backend
- Verificar conexão com banco de dados
