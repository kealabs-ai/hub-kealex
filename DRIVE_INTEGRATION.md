# Integração Google Drive com Agentes IA

Guia de integração da indexação de arquivos do Google Drive para enriquecer prompts de IA.

## Configuração Inicial

### 1. Obter Service Account do Google Cloud

1. Acesse [Google Cloud Console](https://console.cloud.google.com)
2. Crie um novo projeto ou selecione um existente
3. Ative a Google Drive API
4. Crie uma Service Account:
   - Vá para **Service Accounts**
   - Crie uma nova conta de serviço
   - Gere uma chave JSON
5. Compartilhe a pasta do Drive com o email da service account (`seu-sa@seu-projeto.iam.gserviceaccount.com`) com acesso leitura

### 2. Armazenar o JSON da Service Account

Guarde o arquivo JSON gerado. Você precisará enviar seu conteúdo ao criar uma Drive Source.

## Fluxo de Uso

### 1. Criar uma Drive Source

```bash
POST /k1/lex/drive-sources
Authorization: Bearer <seu_token>
Content-Type: application/json

{
  "pasta_id": "1tYK3Bs5P-WuWIUMd5UgFUJnYuCg3AA0D",
  "nome_pasta": "Base de Conhecimento",
  "agente_id": "uuid-do-agente-ia",
  "service_account": "{json_completo_da_service_account}"
}
```

**Resposta:**
```json
{
  "id": "drive-source-uuid",
  "tenant_id": "seu-tenant",
  "agente_id": "uuid-do-agente",
  "pasta_id": "1tYK3Bs5P-WuWIUMd5UgFUJnYuCg3AA0D",
  "nome_pasta": "Base de Conhecimento",
  "ultima_sync": null,
  "ativo": true,
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

### 2. Sincronizar Arquivos

Indexa os arquivos da pasta (deve ser feito periodicamente):

```bash
POST /k1/lex/drive-sources/{source_id}/sincronizar
Authorization: Bearer <seu_token>
```

**Resposta:**
```json
{
  "message": "15 arquivos sincronizados",
  "total": 15,
  "source_id": "drive-source-uuid"
}
```

### 3. Listar Arquivos Indexados

```bash
GET /k1/lex/drive-sources/{source_id}/arquivos
Authorization: Bearer <seu_token>
```

**Resposta:**
```json
[
  {
    "id": "arquivo-uuid",
    "nome": "Politica_Empresa_2024.pdf",
    "tipo": "application/pdf",
    "palavras_chave": "politica empresa",
    "tamanho_bytes": 524288,
    "url": "https://drive.google.com/file/d/...",
    "indexado_em": "2024-01-15T10:35:00"
  },
  {
    "id": "arquivo-uuid-2",
    "nome": "Manual de Processos.docx",
    "tipo": "application/msword",
    "palavras_chave": "manual processos",
    "tamanho_bytes": 204800,
    "url": "https://drive.google.com/file/d/...",
    "indexado_em": "2024-01-15T10:35:00"
  }
]
```

### 4. Enriquecer Prompt com Contexto do Drive

Quando um usuário faz uma consulta ao agente:

```bash
GET /k1/lex/agentes/{agente_id}/drive-contexto?prompt=politica+empresa
Authorization: Bearer <seu_token>
```

**Resposta:**
```json
{
  "arquivos_relevantes": [
    {
      "nome": "Politica_Empresa_2024.pdf",
      "tipo": "application/pdf",
      "url": "https://drive.google.com/file/d/...",
      "score": 2,
      "palavras_chave": "politica empresa"
    }
  ],
  "total_encontrado": 1,
  "prompt_enriquecido": "politica empresa\n\n=== CONTEXTO DO DRIVE ===\nArquivos relevantes:\n- Politica_Empresa_2024.pdf (application/pdf) - https://drive.google.com/file/d/..."
}
```

## Tipos de Arquivo Suportados

- **PDF**: `application/pdf`
- **Google Docs**: `application/vnd.google-apps.document`
- **Google Sheets**: `application/vnd.google-apps.spreadsheet`
- **Word**: `application/msword`
- **Texto**: `text/plain`

## Endpoints Disponíveis

### Drive Sources

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/k1/lex/drive-sources` | Criar nova source |
| GET | `/k1/lex/drive-sources` | Listar todas as sources |
| PUT | `/k1/lex/drive-sources/{source_id}` | Atualizar source |
| POST | `/k1/lex/drive-sources/{source_id}/sincronizar` | Sincronizar arquivos |
| GET | `/k1/lex/drive-sources/{source_id}/arquivos` | Listar arquivos indexados |

### Contexto para IA

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/k1/lex/agentes/{agente_id}/drive-contexto` | Obter contexto enriquecido |

## Algoritmo de Busca

A busca é baseada em **palavras-chave** extraídas do nome do arquivo:

1. Nome do arquivo: `Politica_Empresa_2024.pdf`
2. Processamento: Converte para lowercase, substitui `-` e `_` por espaços, remove palavras com < 3 caracteres
3. Palavras-chave geradas: `politica empresa`
4. Prompt do usuário: `"politica empresa"`
5. Pontuação: Conta quantas palavras do prompt coincidem com as palavras-chave do arquivo
6. Resultados: Ordenados por pontuação decrescente, máximo 10 arquivos por consulta

## Fluxo Recomendado de Integração

1. **Admin configura Drive Source** (uma vez)
   ```
   POST /k1/lex/drive-sources
   ```

2. **Sistema sincroniza periodicamente** (cron job ou background task)
   ```
   POST /k1/lex/drive-sources/{source_id}/sincronizar
   ```
   - Recomendado: A cada 6 horas ou 1 vez ao dia
   - Apenas adiciona novos arquivos, não duplica

3. **Quando usuário consulta a IA**
   ```
   GET /k1/lex/agentes/{agente_id}/drive-contexto?prompt={user_prompt}
   ```

4. **Enriquecer o prompt original**
   - Usar o `prompt_enriquecido` retornado como novo prompt
   - Enviar para a IA junto com os metadados dos arquivos

## Exemplo Completo de Fluxo

### JavaScript/Frontend

```javascript
// 1. Obter contexto do Drive para enriquecer prompt
const response = await fetch(
  `/k1/lex/agentes/${agenteId}/drive-contexto?prompt=${encodeURIComponent(userPrompt)}`,
  {
    headers: { Authorization: `Bearer ${token}` }
  }
);
const { prompt_enriquecido, arquivos_relevantes } = await response.json();

// 2. Enviar prompt enriquecido para a IA
const iaResponse = await fetch(
  `/k1/lex/agentes/${agenteId}/chat`,
  {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      prompt: prompt_enriquecido,
      contexto_arquivos: arquivos_relevantes
    })
  }
);

// 3. Exibir resposta
const resultado = await iaResponse.json();
console.log(resultado.resposta);
console.log('Arquivos consultados:', resultado.arquivos_usados);
```

## Segurança

- **Service Account**: Armazenada encriptada no banco (implementar após)
- **Acesso**: Apenas admins podem criar/editar sources
- **Usuários**: Podem consultar contexto se agente_id estiver vinculado à sua source
- **Permissões**: Google Drive valida automaticamente através da Service Account

## Troubleshooting

### Erro: "Erro ao criar cliente Drive"
- Verifique se o JSON da Service Account é válido
- Confirme que a pasta foi compartilhada com o email da service account

### Nenhum arquivo sincronizado
- Verifique o `pasta_id` (deve ser do Drive, não do URL)
- Confirme que há arquivos suportados na pasta
- Verifique permissões da Service Account

### Prompt não enriquecido
- Verifique se existe uma Drive Source ativa vinculada ao agente
- Confirme que arquivos foram sincronizados
- Use o endpoint `/drive-sources/{source_id}/arquivos` para debug
