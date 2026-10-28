-- Stores the OpenAI API base URL used by the backend chat proxy.
ALTER TABLE cfg_ia_providers
    ADD COLUMN endpoint_url TEXT NULL;
