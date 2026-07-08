# svc-repositorios — Microserviço MCP de Leitura de Repositórios

Microserviço FastAPI para gerenciar e ler repositórios de múltiplas fontes: diretórios locais, CDN e Google Drive.

## Recursos

- **Repositórios Locais**: Leitura de arquivos em diretórios do servidor
- **CDN**: Integração com endpoints JSON de CDN
- **Google Drive**: Acesso a pastas do Google Drive via API
- **Scan Automático**: Indexação de arquivos com metadados
- **Upload**: Envio de arquivos para repositórios locais
- **Multitenancy**: Isolamento de dados por tenant

## Endpoints

### Repositórios

```
GET    /k1/lex/repositorios              # Listar repositórios
POST   /k1/lex/repositorios              # Criar repositório
POST   /k1/lex/repositorios/get          # Obter repositório
POST   /k1/lex/repositorios/update       # Atualizar repositório
POST   /k1/lex/repositorios/delete       # Deletar repositório
```

### Arquivos

```
GET    /k1/lex/repositorios/{repo_id}/arquivos              # Listar arquivos
POST   /k1/lex/repositorios/{repo_id}/scan                  # Escanear repositório
POST   /k1/lex/repositorios/{repo_id}/upload                # Upload de arquivo
GET    /k1/lex/repositorios/{repo_id}/arquivos/{arquivo_id} # Obter arquivo
```

## Exemplos de Uso

### 1. Criar Repositório Local

```json
POST /k1/lex/repositorios
{
  "nome": "Documentos Processos",
  "tipo": "local",
  "caminhoLocal": "/var/documentos/processos",
  "descricao": "Repositório de documentos dos processos"
}
```

### 2. Criar Repositório CDN

```json
POST /k1/lex/repositorios
{
  "nome": "CDN Modelos",
  "tipo": "cdn",
  "url": "https://cdn.example.com/api/files",
  "descricao": "Modelos de documentos do CDN"
}
```

### 3. Criar Repositório Google Drive

```json
POST /k1/lex/repositorios
{
  "nome": "Drive Compartilhado",
  "tipo": "gdrive",
  "gdriveFolder": "1a2b3c4d5e6f7g8h9i0j",
  "descricao": "Pasta compartilhada do Google Drive"
}
```

### 4. Escanear Repositório

```
POST /k1/lex/repositorios/{repo_id}/scan
```

Resposta:
```json
{
  "ok": true,
  "mensagem": "Repositório escaneado com sucesso"
}
```

### 5. Listar Arquivos

```
GET /k1/lex/repositorios/{repo_id}/arquivos
```

Resposta:
```json
[
  {
    "id": "uuid",
    "tenantId": "tenant-id",
    "repositorioId": "repo-id",
    "nome": "documento.pdf",
    "caminho": "documentos/documento.pdf",
    "tipoMime": "application/pdf",
    "tamanhoBytes": 102400,
    "hashArquivo": null,
    "metadados": {},
    "createdAt": "2024-01-15T10:30:00",
    "updatedAt": "2024-01-15T10:30:00"
  }
]
```

### 6. Upload de Arquivo

```
POST /k1/lex/repositorios/{repo_id}/upload
Content-Type: multipart/form-data

file: <arquivo>
```

## Variáveis de Ambiente

```bash
DATABASE_URL=mysql+pymysql://usuario:senha@host:3306/banco
SECRET_KEY=sua_chave_segura
STORAGE_PATH=/tmp/repositorios
GDRIVE_TOKEN=seu_token_google_drive
```

## Estrutura de Dados

### Repositorio
- `id`: UUID único
- `tenant_id`: ID do tenant (multitenancy)
- `user_id`: ID do usuário criador
- `nome`: Nome do repositório
- `tipo`: local | cdn | gdrive
- `status`: ativo | inativo | erro
- `url`: URL do CDN (se aplicável)
- `caminho_local`: Caminho local (se aplicável)
- `gdrive_folder_id`: ID da pasta Google Drive (se aplicável)
- `descricao`: Descrição
- `metadados`: JSON com informações adicionais

### Arquivo
- `id`: UUID único
- `tenant_id`: ID do tenant
- `repositorio_id`: ID do repositório
- `nome`: Nome do arquivo
- `caminho`: Caminho relativo
- `tipo_mime`: MIME type
- `tamanho_bytes`: Tamanho em bytes
- `hash_arquivo`: Hash SHA-256 (opcional)
- `metadados`: JSON com informações adicionais

## Integração com Docker Compose

Adicione ao `docker-compose.yml`:

```yaml
svc-repositorios:
  build: ./svc-repositorios
  container_name: svc-repositorios
  environment:
    DATABASE_URL: ${DATABASE_URL}
    SECRET_KEY: ${SECRET_KEY}
    STORAGE_PATH: /app/storage
    GDRIVE_TOKEN: ${GDRIVE_TOKEN}
  volumes:
    - ./storage:/app/storage
  ports:
    - "8007:8000"
  depends_on:
    - mysql
  networks:
    - kealex-network
```

## Fluxo de Funcionamento

1. **Criar Repositório**: Define a fonte (local, CDN ou Google Drive)
2. **Escanear**: Indexa todos os arquivos da fonte
3. **Listar Arquivos**: Retorna metadados dos arquivos indexados
4. **Upload** (local): Envia novos arquivos para repositório local
5. **Download**: Acessa conteúdo dos arquivos

## Segurança

- Autenticação via JWT
- Isolamento por tenant
- Validação de tipos de repositório
- Tratamento de erros com status apropriado
- CORS configurado

## Próximos Passos

- Implementar cache de metadados
- Adicionar busca full-text
- Suporte a versionamento de arquivos
- Integração com S3/MinIO
- Sincronização automática de repositórios
