-- Extensão para vetores (pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabelas do LiteLLM
CREATE TABLE IF NOT EXISTS litellm_organization (
    organization_id VARCHAR(255) PRIMARY KEY,
    organization_alias VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS litellm_user (
    user_id VARCHAR(255) PRIMARY KEY,
    user_email VARCHAR(255),
    user_role VARCHAR(50),
    organization_id VARCHAR(255) REFERENCES litellm_organization(organization_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Adicionar índices para performance
CREATE INDEX IF NOT EXISTS idx_user_organization ON litellm_user(organization_id);
CREATE INDEX IF NOT EXISTS idx_user_email ON litellm_user(user_email);

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_litellm_user_updated_at 
    BEFORE UPDATE ON litellm_user 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_litellm_organization_updated_at 
    BEFORE UPDATE ON litellm_organization 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();