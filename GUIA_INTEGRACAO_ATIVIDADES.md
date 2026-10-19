# Guia de Integração - Endpoints de Atividade

## Problema
O erro 404 ao criar atividade ocorre porque o endpoint não existe no `app/main.py`.

## Solução
Integrar o modelo `Atividade` e seus endpoints no arquivo `app/main.py`.

## Passos de Integração

### 1. Adicionar o Modelo Atividade
Após a classe `Honorario` (por volta da linha 300), adicione:

```python
class Atividade(Base):
    __tablename__ = "atividades"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    processo_id = Column(String(36), nullable=False)
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    tipo = Column(String(50), default="geral")
    status = Column(String(50), default="pendente")
    prioridade = Column(String(20), default="normal")
    data_vencimento = Column(DateTime, nullable=True)
    data_conclusao = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 2. Adicionar Schemas Pydantic
Após a classe `ProcessoDeleteIn` (por volta da linha 450), adicione:

```python
class AtividadeIn(BaseModel):
    processoId: str
    titulo: str
    descricao: Optional[str] = None
    tipo: str = "geral"
    prioridade: str = "normal"
    dataVencimento: Optional[str] = None


class AtividadeUpdate(BaseModel):
    id: str
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    tipo: Optional[str] = None
    status: Optional[str] = None
    prioridade: Optional[str] = None
    dataVencimento: Optional[str] = None
```

### 3. Adicionar Helper Function
Após a função `_enrich_processos` (por volta da linha 550), adicione:

```python
def _atividade_to_dict(a: Atividade) -> dict:
    return {
        "id": a.id,
        "tenantId": a.tenant_id,
        "userId": a.user_id,
        "processoId": a.processo_id,
        "titulo": a.titulo,
        "descricao": a.descricao,
        "tipo": a.tipo,
        "status": a.status,
        "prioridade": a.prioridade,
        "dataVencimento": a.data_vencimento.isoformat() if a.data_vencimento else None,
        "dataConclusao": a.data_conclusao.isoformat() if a.data_conclusao else None,
        "createdAt": a.created_at.isoformat(),
        "updatedAt": a.updated_at.isoformat(),
    }
```

### 4. Adicionar Endpoints
No final do arquivo (antes da última linha), adicione todos os endpoints do arquivo `ATIVIDADES_ENDPOINTS.py`.

## Endpoints Disponíveis

### Listar Atividades
```
GET /k1/lex/atividades
GET /v1/lex/atividades
```

### Criar Atividade
```
POST /k1/lex/atividades
POST /v1/lex/atividades

Body:
{
  "processoId": "uuid",
  "titulo": "Título da atividade",
  "descricao": "Descrição opcional",
  "tipo": "geral",
  "prioridade": "normal",
  "dataVencimento": "2024-12-31T23:59:59"
}
```

### Obter Atividade
```
POST /k1/lex/atividades/get
POST /v1/lex/atividades/get

Body:
{
  "id": "uuid"
}
```

### Atualizar Atividade
```
POST /k1/lex/atividades/update
POST /v1/lex/atividades/update

Body:
{
  "id": "uuid",
  "titulo": "Novo título",
  "status": "concluida"
}
```

### Deletar Atividade
```
POST /k1/lex/atividades/delete
POST /v1/lex/atividades/delete

Body:
{
  "id": "uuid"
}
```

### Listar Atividades por Processo
```
GET /k1/lex/atividades/processo/{processo_id}
GET /v1/lex/atividades/processo/{processo_id}
```

### Concluir Atividade
```
POST /k1/lex/atividades/concluir
POST /v1/lex/atividades/concluir

Body:
{
  "id": "uuid"
}
```

### Listar Atividades Pendentes
```
GET /k1/lex/atividades/pendentes
GET /v1/lex/atividades/pendentes
```

## Tipos de Atividade
- `geral` - Atividade geral
- `reuniao` - Reunião
- `ligacao` - Ligação
- `email` - Email
- `outro` - Outro tipo

## Prioridades
- `baixa` - Baixa prioridade
- `normal` - Prioridade normal
- `alta` - Alta prioridade
- `urgente` - Urgente

## Status
- `pendente` - Atividade pendente
- `concluida` - Atividade concluída
- `cancelada` - Atividade cancelada

## Migração do Banco de Dados

Execute este SQL para criar a tabela:

```sql
CREATE TABLE atividades (
  id VARCHAR(36) PRIMARY KEY,
  tenant_id VARCHAR(36) NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  processo_id VARCHAR(36) NOT NULL,
  titulo VARCHAR(255) NOT NULL,
  descricao LONGTEXT,
  tipo VARCHAR(50) DEFAULT 'geral',
  status VARCHAR(50) DEFAULT 'pendente',
  prioridade VARCHAR(20) DEFAULT 'normal',
  data_vencimento DATETIME,
  data_conclusao DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_tenant_id (tenant_id),
  INDEX idx_processo_id (processo_id),
  INDEX idx_status (status),
  INDEX idx_data_vencimento (data_vencimento)
);
```

## Próximos Passos

1. Copiar o código do arquivo `ATIVIDADES_ENDPOINTS.py`
2. Integrar no `app/main.py` seguindo os passos acima
3. Executar a migração SQL
4. Reiniciar o container
5. Testar os endpoints via Swagger em `/docs`
