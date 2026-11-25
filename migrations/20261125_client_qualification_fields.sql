ALTER TABLE clientes
    ADD COLUMN rg VARCHAR(30) NULL,
    ADD COLUMN orgao_expedidor VARCHAR(80) NULL,
    ADD COLUMN nacionalidade VARCHAR(80) NULL,
    ADD COLUMN estado_civil VARCHAR(40) NULL,
    ADD COLUMN profissao VARCHAR(120) NULL,
    ADD COLUMN data_nascimento VARCHAR(10) NULL,
    ADD COLUMN razao_social VARCHAR(255) NULL,
    ADD COLUMN nome_fantasia VARCHAR(255) NULL,
    ADD COLUMN inscricao_estadual VARCHAR(40) NULL,
    ADD COLUMN inscricao_municipal VARCHAR(40) NULL,
    ADD COLUMN representante_legal VARCHAR(255) NULL,
    ADD COLUMN whatsapp VARCHAR(50) NULL;
