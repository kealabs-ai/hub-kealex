# Per-user AI credentials deployment

1. Apply `create_user_api_keys.sql` to the Kealex database before deploying either backend.
2. Set the same persistent `KEALEX_API_KEYS_ENCRYPTION_KEY` value in `hubkealex` and `svc-configuracoes`. Generate one with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
3. Keep that encryption key backed up and unchanged. Credentials saved with one key cannot be decrypted after rotating it.

For backward compatibility, both services derive a Fernet key from the JWT secret when `KEALEX_API_KEYS_ENCRYPTION_KEY` is absent. Configure the dedicated variable in production so encryption is independent from JWT signing.

The previous tenant-wide `cfg_ia` and `cfg_ia_providers` values remain available as a chat fallback. They are not copied to individual users. A user's active personal provider/model takes precedence; for a selected agent, a personal key is used only when its provider and model match the agent.
