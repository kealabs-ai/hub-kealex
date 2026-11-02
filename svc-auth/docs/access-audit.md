# Auditoria de decisões de acesso

O `require_active_trial` continua decidindo o acesso sincronamente com o estado do tenant no MySQL. Depois da decisão, o serviço publica apenas metadados (`tenant_id`, `user_id`, decisão, horário e ID do evento) na fila durável `kealex.access.audit` do RabbitMQ. O consumidor registra esses metadados no log estruturado do serviço.

RabbitMQ é opcional fora do Compose. Configure `KEALEX_RABBITMQ_HOST`, `KEALEX_RABBITMQ_PORT`, `KEALEX_RABBITMQ_USER` e `KEALEX_RABBITMQ_PASSWORD`. Falhas do broker não concedem acesso e não interrompem a decisão; em indisponibilidade prolongada, o buffer local é limitado e alguns eventos de auditoria podem ser descartados. Monitore `/metrics`, que expõe contadores sem labels de tenant/usuário para evitar cardinalidade e exposição de dados.
