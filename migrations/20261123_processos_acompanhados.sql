CREATE TABLE IF NOT EXISTS processos_acompanhados (
  id VARCHAR(36) NOT NULL PRIMARY KEY, tenant_id VARCHAR(36) NOT NULL, user_id VARCHAR(36) NOT NULL,
  scope_key VARCHAR(36) NOT NULL, numero_processo VARCHAR(20) NOT NULL, tribunal VARCHAR(255) NULL,
  classe_processual VARCHAR(255) NULL, assunto VARCHAR(1000) NULL, fase_atual VARCHAR(255) NULL,
  situacao VARCHAR(255) NULL, data_ultima_movimentacao VARCHAR(100) NULL, ultima_consulta_em DATETIME NOT NULL,
  dados JSON NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
  UNIQUE KEY uq_processo_acompanhado_scope_numero (tenant_id, scope_key, numero_processo),
  KEY ix_processos_acompanhados_tenant_id (tenant_id)
);
CREATE TABLE IF NOT EXISTS historico_consultas_processuais (
  id VARCHAR(36) NOT NULL PRIMARY KEY, tenant_id VARCHAR(36) NOT NULL, processo_id VARCHAR(36) NULL,
  numero_processo VARCHAR(20) NOT NULL, usuario_solicitante_id VARCHAR(36) NOT NULL, fornecedor VARCHAR(80) NOT NULL,
  status_http INT NULL, status_consulta VARCHAR(255) NOT NULL, houve_alteracao INT NULL,
  data_ultima_movimentacao VARCHAR(100) NULL, consultado_em DATETIME NOT NULL,
  KEY ix_historico_consultas_tenant_id (tenant_id), KEY ix_historico_consultas_processo_id (processo_id),
  KEY ix_historico_consultas_consultado_em (consultado_em),
  CONSTRAINT fk_historico_consultas_processo FOREIGN KEY (processo_id) REFERENCES processos_acompanhados(id)
);
