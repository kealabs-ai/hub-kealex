# Migração de Endpoints de Cobrança para svc-cobrancas

## 📋 Resumo

Os endpoints de cobrança foram migrados do `app/main.py` para um novo microserviço dedicado `svc-cobrancas`, seguindo o padrão arquitetural do projeto.

## 🏗️ Estrutura Criada

```
svc-cobrancas/
├── main.py              # Aplicação FastAPI
├── requirements.txt     # Dependências Python
├── Dockerfile          # Build da imagem Docker
└── README.md           # Documentação
```

## 📦 Arquivos Criados

### 1. `svc-cobrancas/main.py`
- Modelos: `Cobranca` e `HistoricoCobranca`
- 7 endpoints principais
- Logging detalhado
- Tratamento de erros

### 2. `svc-cobrancas/requirements.txt`
- FastAPI 0.104.1
- SQLAlchemy 2.0.23
- PyMySQL 1.1.0
- python-jose 3.3.0

### 3. `svc-cobrancas/Dockerfile`
- Python 3.11-slim
- Porta 8000
- Uvicorn como servidor

### 4. `docker-compose.yml` (atualizado)
- Novo serviço `svc-cobrancas`
- Porta 8001 (local)
- Integração com Traefik
- Health checks

## 🔄 Endpoints Migrados

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/k1/lex/cobrancas` | POST | Criar cobrança |
| `/k1/lex/cobrancas` | GET | Listar cobrancas |
| `/k1/lex/cobrancas/get` | POST | Obter cobrança |
| `/k1/lex/cobrancas/proxima-fase` | POST | Avançar fase |
| `/k1/lex/cobrancas/marcar-pago` | POST | Marcar como pago |
| `/k1/lex/cobrancas/cancelar` | POST | Cancelar cobrança |
| `/k1/lex/cobrancas/timeline` | POST | Ver timeline |

## 🚀 Como Usar

### Build Local
```bash
cd svc-cobrancas
docker build -t svc-cobrancas .
```

### Executar com Docker Compose
```bash
docker compose up svc-cobrancas
```

### Testar Health Check
```bash
curl http://localhost:8001/health
```

### Exemplo de Requisição
```bash
curl -X POST http://localhost:8001/k1/lex/cobrancas \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "processoId": "uuid",
    "clienteId": "uuid",
    "valorCentavos": 10000,
    "dataVencimento": "2024-12-31T23:59:59"
  }'
```

## 📊 Fases de Cobrança

0. **Pendente** - Criada, aguardando processamento
1. **Aguardando Pagamento** - Aguardando confirmação
2. **Vencida** - Prazo vencido
3. **Em Cobrança** - Processo ativo
4. **Pago** - Concluída

## 🔐 Segurança

- Autenticação via JWT (Bearer token)
- Isolamento por tenant_id
- Validação de entrada
- Logging de todas as ações

## 📝 Logging

Todos os eventos são registrados com prefixo:
- `[CREATE_COBRANCA]` - Criação
- `[LIST_COBRANCAS]` - Listagem
- `[GET_COBRANCA]` - Obtenção
- `[PROXIMA_FASE]` - Avanço de fase
- `[MARCAR_PAGO]` - Marcação de pagamento
- `[CANCELAR]` - Cancelamento
- `[TIMELINE]` - Timeline

## 🔄 Próximos Passos

1. ✅ Criar microserviço svc-cobrancas
2. ✅ Adicionar ao docker-compose.yml
3. ⏳ Remover endpoints de cobrança do app/main.py (opcional)
4. ⏳ Atualizar frontend para usar novo endpoint
5. ⏳ Testar em produção

## 📚 Referências

- Padrão de microserviços: `svc-processos`, `svc-clientes`, etc.
- Documentação: `svc-cobrancas/README.md`
- Fluxo de cobrança: `FLUXO_COBRANCA.md`

## ⚠️ Notas Importantes

- O microserviço usa o mesmo banco de dados
- Mantém compatibilidade com endpoints existentes
- Pode rodar em paralelo com app/main.py
- Traefik roteia automaticamente para o serviço correto
