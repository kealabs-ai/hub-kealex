# Kealex API - Coleções Postman

## 📋 Visão Geral

Esta pasta contém as coleções do Postman para testar todas as APIs do sistema Kealex.

## 📁 Arquivos

- `Kealex-Processos-API.postman_collection.json` - Coleção completa para módulo de processos
- `Kealex-Environment.postman_environment.json` - Environment com variáveis do projeto

## 🚀 Como Usar

### 1. Importar no Postman

1. Abra o Postman
2. Clique em **Import**
3. Selecione os arquivos `.json` desta pasta
4. Importe tanto a **Collection** quanto o **Environment**

### 2. Configurar Environment

1. No Postman, selecione o environment **"Kealex - Local Development"**
2. Verifique se a variável `base_url` está configurada para `http://localhost:8000`
3. As demais variáveis serão preenchidas automaticamente durante os testes

### 3. Executar Testes

#### Ordem Recomendada:

1. **🔐 Autenticação > Login**
   - Executa o login e salva o token automaticamente
   - Credenciais padrão: `admin@kealex.com` / `admin123`

2. **📋 Processos - CRUD > Listar Processos**
   - Lista processos existentes
   - Salva automaticamente o ID do primeiro processo

3. **📋 Processos - CRUD > Criar Processo**
   - Cria um novo processo
   - **IMPORTANTE**: Você precisa ter um `cliente_id` válido
   - Salva automaticamente o ID do processo criado

4. **📋 Processos - CRUD > Buscar/Atualizar/Deletar**
   - Usa o `processo_id` salvo automaticamente

## 📊 Estrutura da Coleção

### 🔐 Autenticação
- **Login**: Obtém token JWT
- **Verificar Token**: Valida token atual

### 📋 Processos - CRUD
- **Listar Processos**: `GET /processos`
- **Buscar por ID**: `POST /processos/get`
- **Criar Processo**: `POST /processos`
- **Atualizar Processo**: `POST /processos/update`
- **Deletar Processo**: `POST /processos/delete`

### 🧪 Testes de Status
- **Status - Ativo**: Altera status para "ativo"
- **Status - Arquivado**: Altera status para "arquivado"
- **Status - Encerrado**: Altera status para "encerrado"

### ❌ Testes de Erro
- **Processo Inexistente**: Testa erro 404
- **Cliente Inexistente**: Testa validação de cliente
- **Sem Autenticação**: Testa erro 401

## 🔧 Variáveis Automáticas

As seguintes variáveis são preenchidas automaticamente:

- `access_token` - Token JWT do login
- `processo_id` - ID do último processo criado/listado
- `cliente_id` - ID do cliente (precisa ser configurado manualmente)

## 📝 Exemplo de Payload - Criar Processo

```json
{
  "numero": "5001234-12.2024.8.26.0001",
  "titulo": "Ação de Cobrança - Teste Postman",
  "descricao": "Processo de cobrança de valores em atraso referente a prestação de serviços jurídicos.",
  "clienteId": "{{cliente_id}}",
  "vara": "1ª Vara Cível da Comarca de São Paulo",
  "tribunal": "Tribunal de Justiça de São Paulo",
  "escritorioId": null
}
```

## ⚠️ Pré-requisitos

1. **Sistema rodando**: `docker compose up --build`
2. **Cliente cadastrado**: Você precisa ter pelo menos um cliente no sistema
3. **Token válido**: Execute o login antes dos demais testes

## 🔍 Como Obter cliente_id

1. Execute o login
2. Acesse `GET {{base_url}}/clientes` (se disponível)
3. Ou consulte diretamente no banco de dados
4. Configure a variável `cliente_id` no environment

## 📈 Status de Processo

Os status válidos são:
- `ativo` - Processo em andamento
- `arquivado` - Processo arquivado
- `encerrado` - Processo finalizado

## 🐛 Troubleshooting

### Erro 401 (Unauthorized)
- Verifique se executou o login
- Confirme se o token está sendo enviado no header

### Erro 404 (Not Found)
- Verifique se o `processo_id` existe
- Confirme se o `cliente_id` é válido

### Erro 500 (Internal Server Error)
- Verifique se o banco de dados está rodando
- Confirme se as variáveis de ambiente estão corretas

## 🔄 Executar Toda a Coleção

Para executar todos os testes automaticamente:

1. Clique nos **3 pontos** da coleção
2. Selecione **Run collection**
3. Configure a ordem de execução
4. Execute com delay de 1-2 segundos entre requests

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique se o sistema está rodando em `http://localhost:8000`
2. Confirme se o login está funcionando
3. Verifique os logs do Docker: `docker compose logs svc-processos`