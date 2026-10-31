# svc-usuarios

## Responsabilidade

Gerenciar usuários de cada tenant, seus vínculos com escritórios, modalidade de atuação, chaves públicas do DataJud e consultas processuais no DataJud.

## Camadas

- API: `app/api/routes/`, schemas em `app/api/schemas/` e dependências em `app/api/dependencies.py`.
- Casos de uso: `app/application/use_cases/`.
- Domínio: `app/domain/entities/`.
- Persistência e segurança: `app/infrastructure/database/` e `app/infrastructure/security/`.
- Configuração: `app/core/`.

O `main.py` da raiz mantém compatibilidade com `uvicorn main:app` no Docker e importa `app.main`. Preserve essa entrada e os contratos HTTP existentes.

## Funcionalidades

- Listagem, consulta, cadastro, atualização e exclusão de usuários.
- Controle de acesso para administradores e escritórios.
- Associação ou remoção de usuário em escritório e validação do limite de advogados.
- Consulta e atualização da modalidade do próprio usuário.
- Cadastro, listagem, atualização e exclusão de chaves públicas do DataJud.
- Consulta de processo por tribunal e número CNJ via DataJud.
- Consulta da identidade autenticada e health check.

## Dependências

- MySQL compartilhado via SQLAlchemy e PyMySQL.
- JWT HS256 via `python-jose`.
- Hash de senha via `bcrypt`.
- API pública DataJud via `urllib` da biblioteca padrão.
- FastAPI, Pydantic e Uvicorn.

## Regras

- Filtrar usuários por `tenant_id`; operações de escritório também restringem por `escritorio_id`.
- Apenas administradores podem excluir usuários. Escritórios podem gerenciar apenas advogados vinculados ao próprio escritório.
- Validar a capacidade do escritório antes de adicionar advogados ativos; preservar as mensagens/status HTTP existentes.
- Segredos e chaves públicas devem permanecer fora de logs e respostas que não precisem deles.
- Chaves públicas são associadas ao usuário e únicas por órgão; validar e normalizar os dados conforme as regras atuais.
- Consultas DataJud exigem usuário autenticado, tribunal suportado, número CNJ com 20 dígitos e chave pública configurada para o ramo da Justiça.
- Não alterar schema sem migração versionada. `Base.metadata.create_all()` cria tabelas ausentes, mas não altera as existentes.
- Preservar os nomes e aliases de campos camelCase usados pelos clientes.

## Como alterar

- CRUD, modalidade e identidade: `app/api/routes/user_routes.py`.
- Chaves públicas: `app/api/routes/public_key_routes.py`.
- Consulta DataJud: `app/api/routes/datajud_routes.py`.
- Schemas HTTP: `app/api/schemas/user_schema.py`.
- Limite de advogados: `app/application/use_cases/office_capacity.py`.
- Serialização de respostas: `app/application/use_cases/user_presenter.py`.
- Enum de papel: `app/domain/entities/role.py`.
- Modelos e sessões: `app/infrastructure/database/`.
- JWT e bcrypt: `app/infrastructure/security/`.
- Configuração: `app/core/config.py`.
- Ao alterar contratos ou regras, atualizar também `knowledge.md` e os consumidores pertinentes.

## Testes, ambiente e build

Os testes usam `unittest`. Use Python 3.12, alinhado ao `Dockerfile` e às versões fixadas. No PowerShell, a partir da raiz de `svc-usuarios`:

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests/unit -v
python -m unittest discover -s tests/integration -v
docker build -t svc-usuarios:teste .
docker image ls svc-usuarios
```
