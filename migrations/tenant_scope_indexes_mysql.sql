-- MySQL one-time migration. Review SHOW INDEX first and skip any index that
-- already exists under a different name. Roll out during a low-traffic window.
-- These indexes support the most frequent tenant-scoped list/filter queries.
ALTER TABLE documentos
  ADD INDEX ix_documentos_tenant_processo (tenant_id, processo_id);

ALTER TABLE clientes
  ADD INDEX ix_clientes_tenant_created (tenant_id, created_at);

ALTER TABLE cobrancas
  ADD INDEX ix_cobrancas_tenant_created (tenant_id, created_at);

ALTER TABLE activities
  ADD INDEX ix_activities_tenant_user_status (tenant_id, user_id, status, created_at);
