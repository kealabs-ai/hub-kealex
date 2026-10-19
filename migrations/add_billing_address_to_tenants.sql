-- Migration: adicionar campos de endereço e dados do titular na tabela tenants
ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS billing_name         VARCHAR(255) NULL COMMENT 'Nome completo do titular',
    ADD COLUMN IF NOT EXISTS billing_email        VARCHAR(255) NULL COMMENT 'E-mail do titular',
    ADD COLUMN IF NOT EXISTS billing_postal_code  VARCHAR(10)  NULL COMMENT 'CEP do titular',
    ADD COLUMN IF NOT EXISTS billing_address      VARCHAR(255) NULL COMMENT 'Rua/logradouro do titular',
    ADD COLUMN IF NOT EXISTS billing_address_number VARCHAR(20) NULL COMMENT 'Número do endereço',
    ADD COLUMN IF NOT EXISTS billing_complement   VARCHAR(100) NULL COMMENT 'Complemento do endereço',
    ADD COLUMN IF NOT EXISTS billing_neighborhood VARCHAR(100) NULL COMMENT 'Bairro do titular',
    ADD COLUMN IF NOT EXISTS billing_city         VARCHAR(100) NULL COMMENT 'Cidade do titular',
    ADD COLUMN IF NOT EXISTS billing_state        VARCHAR(2)   NULL COMMENT 'UF do titular';
