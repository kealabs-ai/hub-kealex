# svc-integracoes

## Responsabilidade

Encapsular integrações de provedores externos. O serviço passa a atender as APIs existentes de certidões e consultas fiscais via FiscalAPI, preservando os caminhos públicos usados pelo cliente.

## Camadas

- Rotas e schemas HTTP: `app/api/routes/`
- Casos de uso: `app/application/use_cases/`
- Validação de documentos: `app/domain/`
- Adapter FiscalAPI: `app/infrastructure/fiscalapi_adapter.py`
- Persistência e sessão: `app/infrastructure/database/`
- JWT e tenant ativo: `app/infrastructure/security/`

## Operação

Configure as variáveis FiscalAPI no container `svc-integracoes`. A rota externa `/api/v1/certidoes` é encaminhada pelo Traefik ou pelo Nginx do gateway. O serviço acessa o banco compartilhado e necessita das tabelas criadas por `migrations/create_fiscalapi_consultas.sql`.

## Segurança

Todas as rotas de consulta exigem JWT e role autorizada. Os registros são filtrados simultaneamente por `tenant_id` e `user_id`. POSTs exigem `Idempotency-Key`; a reutilização com parâmetros diferentes resulta em HTTP 409. PDFs são cifrados em repouso e servidos apenas ao proprietário autenticado.
