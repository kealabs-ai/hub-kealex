# Implementação Completa - Endpoints de Processos

## 📋 Resumo das Alterações

### Backend (svc-processos)

#### 1. **Novas Tabelas**
- **Tabela `fases`**: Armazena as fases de cada processo
  - `id`: UUID único
  - `processo_id`: Referência ao processo
  - `label`: Nome da fase (ex: "Protocolo", "Citação")
  - `ordem`: Ordem sequencial da fase
  - `status`: "concluida", "ativa" ou "futura"
  - `data_conclusao`: Data quando a fase foi concluída

#### 2. **Alterações na Tabela `processos`**
- Adicionada coluna `fase_atual` (INT, default 0) para rastrear a fase atual

#### 3. **Novos Endpoints**

**POST `/k1/lex/processos/avancar-fase`**
- Avança o processo para a próxima fase
- Request:
  ```json
  {
    "id": "uuid-do-processo",
    "novaFase": 1
  }
  ```
- Response: Objeto Processo atualizado com fases
- Atualiza automaticamente:
  - Status das fases anteriores para "concluida"
  - Status da fase atual para "ativa"
  - Status das fases futuras para "futura"
  - Data de conclusão das fases completadas

#### 4. **Alterações em Endpoints Existentes**

**POST `/k1/lex/processos` (Create)**
- Agora cria automaticamente 6 fases padrão:
  1. Protocolo (ativa)
  2. Citação
  3. Contestação
  4. Sentença
  5. Recurso
  6. Encerrado

**GET `/k1/lex/processos` (List)**
- Retorna agora com array `fases` e `faseAtual`

**POST `/k1/lex/processos/get` (Get)**
- Retorna agora com array `fases` e `faseAtual`

### Frontend (ViewKealex)

#### 1. **API Client (`src/api/processos.ts`)**
- Novo método: `avancarFase(id: string, novaFase: number)`

#### 2. **Hook (`src/hooks/useProcessos.ts`)**
- Novo hook: `useAvancarFase()`
- Mutation que invalida cache de processos após sucesso

#### 3. **Página (`src/pages/ProcessosPage.tsx`)**
- Integração do hook `useAvancarFase`
- Callback `onAvancar` agora chama o endpoint real
- Timeline expandível mostra fases com status visual

#### 4. **Componente (`src/components/ProcessoTimeline.tsx`)**
- Já estava pronto para receber fases do backend
- Exibe status visual: ✓ (concluída), ● (ativa), ○ (futura)
- Botão "Avançar Fase" funcional para advogados

## 🚀 Passos de Implementação

### 1. Banco de Dados
```bash
# Execute a migração SQL
mysql -u u549746795_kealex -p u549746795_kealex < migrations/add_fases_to_processos.sql
```

### 2. Backend
```bash
cd svc-processos
pip install -r requirements.txt
# Reiniciar o serviço
```

### 3. Frontend
```bash
cd ViewKealex
npm install
npm run dev
```

## 📊 Fluxo de Dados

```
ProcessosPage
  ├── useProcessos() → GET /k1/lex/processos
  │   └── Retorna: Processo[] com fases[]
  │
  ├── ProcessoTimeline
  │   ├── Exibe fases com status visual
  │   └── onAvancar() → useAvancarFase()
  │       └── POST /k1/lex/processos/avancar-fase
  │           └── Atualiza fase_atual e status das fases
  │
  └── Invalidação de cache
      └── useProcessos() refetch automático
```

## ✅ Funcionalidades Implementadas

- ✅ Criar processo com fases padrão
- ✅ Listar processos com fases
- ✅ Avançar fase do processo
- ✅ Rastrear status de cada fase
- ✅ Data de conclusão automática
- ✅ Timeline visual interativa
- ✅ Controle de acesso (apenas advogados podem avançar)
- ✅ Cache invalidation automático

## 🔒 Segurança

- Validação de tenant_id em todos os endpoints
- Verificação de permissões (role-based)
- Clientes só veem seus próprios processos
- Advogados veem processos que criaram
- Admins veem todos os processos do tenant

## 📝 Notas

- Fases são criadas automaticamente ao criar um processo
- Não é possível pular fases (apenas avançar sequencialmente)
- Clientes podem visualizar mas não podem avançar fases
- Cada fase tem data de conclusão registrada automaticamente
