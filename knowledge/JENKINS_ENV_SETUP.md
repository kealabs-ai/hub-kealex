# Configuração de ambiente do Kealex

## Backend

Copie `.env.example` para `.env` na raiz do backend e preencha os valores reais. O arquivo `.env` é ignorado pelo Git e lido pelo Docker Compose; mantenha-o fora do controle de versão e das imagens.

Configurações principais:

- `KEALEX_DATABASE_URL`: URL SQLAlchemy do MySQL com usuário e senha em percent-encoding.
- `KEALEX_JWT_SECRET` e `KEALEX_SECRET_KEY`: devem usar a mesma chave em todos os serviços que assinam ou validam tokens.
- `KEALEX_ASAAS_API_KEY` e `KEALEX_ASAAS_WEBHOOK_TOKEN`: credenciais privadas do Asaas, somente no backend.
- `KEALEX_GEMINI_API_KEY`, `KEALEX_OPENAI_API_KEY`, `KEALEX_GROQ_API_KEY`, `KEALEX_ANTHROPIC_API_KEY` e `KEALEX_CEREBRAS_API_KEY`: chaves privadas de IA, somente no backend.
- `KEALEX_PUBLIC_API_HOST`, `KEALEX_PUBLIC_APP_URL` e `KEALEX_CORS_ALLOWED_ORIGINS`: endereços públicos não secretos usados no roteamento e CORS.

Para gerar uma chave JWT forte:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Jenkins

Cadastre `KEALEX_DATABASE_URL` e `KEALEX_SECRET_KEY` como credenciais secretas no Jenkins. Os Jenkinsfiles referenciam a credencial `kealex-database-url`; o identificador deve existir no Jenkins antes do deploy. Não imprima esses valores nos logs do pipeline.

## Frontend

Copie o `.env.example` do frontend para `.env` e configure `KEALEX_API_BASE_URL`. Valores `VITE_*` são incluídos no bundle do navegador; não coloque chaves privadas, tokens de gateway ou senhas nesses valores.