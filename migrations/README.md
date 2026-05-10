# Migração - Suporte Multi-Provider IA

## Objetivo
Adicionar suporte para múltiplos providers de IA (Cerebras e Groq) no sistema Kealex.

## Alterações no Banco de Dados

### 1. Executar Migração SQL
```bash
mysql -u u549746795_kealex -p u549746795_kealex < migrations/add_provider_to_cfg_ia.sql
```

Ou execute manualmente:
```sql
ALTER TABLE cfg_ia 
ADD COLUMN provider VARCHAR(50) DEFAULT 'cerebras' AFTER escritorio_id;

UPDATE cfg_ia 
SET provider = 'cerebras' 
WHERE provider IS NULL;
```

## Alterações no Backend

### 1. Reiniciar Serviço de Configurações
```bash
cd svc-configuracoes
docker-compose restart svc-configuracoes
```

Ou se estiver rodando localmente:
```bash
cd svc-configuracoes
python main.py
```

## Alterações no Frontend

### 1. Instalar Dependências (se necessário)
```bash
cd ViewKealex
npm install
```

### 2. Reiniciar Servidor de Desenvolvimento
```bash
npm run dev
```

## Verificação

### 1. Testar Endpoint de Configuração IA
```bash
curl -X GET http://localhost:8000/configuracoes/ia \
  -H "Authorization: Bearer SEU_TOKEN_ADMIN"
```

Resposta esperada:
```json
{
  "tenant_id": "...",
  "provider": "cerebras",
  "api_key": null,
  "modelo": "llama-3.3-70b",
  "max_tokens": 8192,
  "system_prompt": null,
  "updated_at": "2025-01-XX..."
}
```

### 2. Testar Salvamento
```bash
curl -X POST http://localhost:8000/configuracoes/ia \
  -H "Authorization: Bearer SEU_TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "groq",
    "api_key": "gsk-...",
    "modelo": "llama-3.3-70b-versatile",
    "max_tokens": 8192
  }'
```

### 3. Testar Interface Admin
1. Faça login como Admin
2. Acesse **Configurações → Agentes IA**
3. Selecione um provider (Cerebras ou Groq)
4. Insira uma API Key
5. Clique em **Salvar Configuração**
6. Verifique a mensagem "Salvo com sucesso"
7. Confirme que permaneceu na mesma aba

### 4. Testar Chat IA
1. Acesse **Kealex AI** no menu
2. Faça uma pergunta
3. Verifique se a resposta é gerada corretamente

## Rollback

Se necessário reverter as alterações:

### 1. Banco de Dados
```sql
ALTER TABLE cfg_ia DROP COLUMN provider;
```

### 2. Backend
Reverta o arquivo `svc-configuracoes/main.py` para a versão anterior

### 3. Frontend
```bash
cd ViewKealex
git checkout HEAD~1 src/pages/AdminPage.tsx
git checkout HEAD~1 src/api/ai.ts
```

## Troubleshooting

### Erro: "Column 'provider' doesn't exist"
Execute a migração SQL novamente

### Erro: "API key inválida"
Verifique se o prefixo está correto:
- Cerebras: `csk-...`
- Groq: `gsk-...`

### Erro: "Provider inválido"
Use apenas `cerebras` ou `groq`

### Configuração não salva
1. Verifique o console do navegador (F12)
2. Verifique os logs do backend
3. Confirme que o token JWT é válido
4. Confirme que o usuário é Admin

## Suporte

Para problemas, contate: suporte@kealex.com.br
