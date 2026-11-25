-- Relaciona clientes existentes a processos e cadastra as demais partes envolvidas.
CREATE TABLE IF NOT EXISTS processo_clientes (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    processo_id VARCHAR(36) NOT NULL,
    cliente_id VARCHAR(36) NOT NULL,
    posicao_processual VARCHAR(80) NOT NULL DEFAULT 'Interessado',
    polo_processual VARCHAR(40) NULL,
    cliente_principal TINYINT(1) NOT NULL DEFAULT 0,
    snapshot_qualificacao JSON NULL,
    observacoes TEXT NULL,
    criado_por VARCHAR(36) NOT NULL,
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_processo_cliente (processo_id, cliente_id),
    KEY ix_processo_clientes_tenant (tenant_id),
    KEY ix_processo_clientes_processo (processo_id),
    KEY ix_processo_clientes_cliente (cliente_id),
    CONSTRAINT fk_processo_clientes_processo FOREIGN KEY (processo_id) REFERENCES processos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS processo_partes (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    processo_id VARCHAR(36) NOT NULL,
    nome VARCHAR(255) NOT NULL,
    tipo_pessoa VARCHAR(20) NOT NULL DEFAULT 'fisica',
    documento VARCHAR(30) NULL,
    email VARCHAR(255) NULL,
    telefone VARCHAR(50) NULL,
    endereco VARCHAR(500) NULL,
    posicao_processual VARCHAR(80) NOT NULL DEFAULT 'Interessado',
    dados_desconhecidos TINYINT(1) NOT NULL DEFAULT 0,
    criado_por VARCHAR(36) NOT NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY ix_processo_partes_tenant (tenant_id),
    KEY ix_processo_partes_processo (processo_id),
    CONSTRAINT fk_processo_partes_processo FOREIGN KEY (processo_id) REFERENCES processos(id) ON DELETE CASCADE
);

-- Preserva e migra o vínculo único legado como cliente principal.
INSERT INTO processo_clientes (
    id, tenant_id, processo_id, cliente_id, posicao_processual, cliente_principal,
    snapshot_qualificacao, criado_por, ativo
)
SELECT UUID(), p.tenant_id, p.id, p.cliente_id, 'Interessado', 1,
       JSON_OBJECT('nome', c.nome, 'email', c.email, 'telefone', c.telefone,
                   'cpfCnpj', c.cpf_cnpj, 'cep', c.cep, 'endereco', c.endereco,
                   'cidade', c.cidade, 'estado', c.estado, 'rg', c.rg,
                   'orgaoExpedidor', c.orgao_expedidor, 'nacionalidade', c.nacionalidade,
                   'estadoCivil', c.estado_civil, 'profissao', c.profissao,
                   'dataNascimento', c.data_nascimento, 'razaoSocial', c.razao_social,
                   'nomeFantasia', c.nome_fantasia, 'inscricaoEstadual', c.inscricao_estadual,
                   'inscricaoMunicipal', c.inscricao_municipal, 'representanteLegal', c.representante_legal,
                   'whatsapp', c.whatsapp),
       p.user_id, 1
FROM processos p
JOIN clientes c ON c.id = p.cliente_id AND c.tenant_id = p.tenant_id
LEFT JOIN processo_clientes pc ON pc.processo_id = p.id AND pc.cliente_id = p.cliente_id
WHERE pc.id IS NULL;
