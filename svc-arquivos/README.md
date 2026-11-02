# svc-arquivos

Serviço opcional de upload/download autenticado. Os arquivos são gravados em `UPLOAD_DIR/<tenant UUID>/<user UUID>/<file UUID>`; o nome informado pelo usuário não é usado como caminho. O endpoint requer JWT assinado pelo Kealex e limita o corpo por `MAX_UPLOAD_BYTES`.

Em `docker-compose.yml`, o serviço monta o named volume `kealex-uploads` e não define `container_name`, permitindo `docker compose up --scale svc-arquivos=3`. O volume local é compartilhado pelas réplicas no mesmo host Docker. Em escala multi-host, substitua-o por um volume compartilhado compatível com Docker (por exemplo, NFS) e valide locking/permissões; named volumes locais não sincronizam entre hosts.

Endpoints: `POST /v1/lex/arquivos`, `GET /v1/lex/arquivos/{id}`, `DELETE /v1/lex/arquivos/{id}`. O serviço não substitui ainda o upload usado pela análise documental, que persiste extrações no MySQL.
