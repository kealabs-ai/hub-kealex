CREATE TABLE IF NOT EXISTS analise_documentos_conversas (
  id VARCHAR(36) NOT NULL PRIMARY KEY,
  tenant_id VARCHAR(36) NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  titulo VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  INDEX ix_analise_conversa_owner (tenant_id, user_id, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS analise_documentos_arquivos (
  id VARCHAR(36) NOT NULL PRIMARY KEY,
  tenant_id VARCHAR(36) NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  conversa_id VARCHAR(36) NOT NULL,
  nome VARCHAR(255) NOT NULL,
  extensao VARCHAR(10) NOT NULL,
  tamanho_bytes INT NOT NULL,
  paginas INT NULL,
  chunks_json LONGTEXT NOT NULL,
  created_at DATETIME NOT NULL,
  INDEX ix_analise_documento_owner (tenant_id, user_id, conversa_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS analise_documentos_mensagens (
  id VARCHAR(36) NOT NULL PRIMARY KEY,
  tenant_id VARCHAR(36) NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  conversa_id VARCHAR(36) NOT NULL,
  role VARCHAR(20) NOT NULL,
  content LONGTEXT NOT NULL,
  created_at DATETIME NOT NULL,
  INDEX ix_analise_mensagem_owner (tenant_id, user_id, conversa_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;