# Instruções do agente — svc-integracoes

- Mantenha rotas, casos de uso, integrações externas e persistência nas camadas correspondentes em `app/`.
- Preserve os paths `/api/v1/certidoes/*`, respostas, estados e regras de idempotência.
- Toda consulta deve ser isolada pelo tenant e usuário do JWT autenticado.
- Nunca registre nem retorne a chave FiscalAPI, identificadores completos ou respostas sem a proteção definida.
- A tabela compartilhada exige a migration `migrations/create_fiscalapi_consultas.sql` nos bancos existentes.
- Preserve a entrada `uvicorn main:app` e `GET /health`.
