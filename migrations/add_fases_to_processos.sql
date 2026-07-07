-- Adicionar coluna fase_atual à tabela processos
ALTER TABLE processos ADD COLUMN fase_atual INT DEFAULT 0;

-- Criar tabela de fases
CREATE TABLE IF NOT EXISTS fases (
    id VARCHAR(36) PRIMARY KEY,
    processo_id VARCHAR(36) NOT NULL,
    label VARCHAR(255) NOT NULL,
    ordem INT NOT NULL,
    status VARCHAR(50) DEFAULT 'futura',
    data_conclusao DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (processo_id) REFERENCES processos(id) ON DELETE CASCADE,
    INDEX idx_processo_id (processo_id),
    INDEX idx_ordem (ordem)
);
