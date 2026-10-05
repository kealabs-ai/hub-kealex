# Comparação: HubKealex vs HubLuisEden

## Problema Identificado

O HubKealex estava falhando ao conectar com o banco de dados quando a senha continha caracteres especiais (`@!@`), enquanto o HubLuisEden funciona corretamente.

## Causa Raiz

**HubKealex (QUEBRADO):**
```python
# app/main.py - linha 28-40
url = URL.create(
    drivername="mysql+pymysql",
    username=username,
    password=password,  # ← Passa a senha RAW sem escapar
    host=host,
    port=int(port),
    database=database,
)
```

**HubLuisEden (FUNCIONANDO):**
```python
# app/database.py - linha 47-50
from urllib.parse import quote_plus

return (
    f"mysql+pymysql://{self.user}:{quote_plus(self.password)}@"
    f"{self.host}:{self.port}/{self.name}"
)
```

## Solução Aplicada

Atualizar `app/main.py` para usar `quote_plus()` ao construir a URL de conexão:

```python
from urllib.parse import quote_plus

def _get_database_url():
    host = os.getenv("KEALEX_DB_HOST")
    database = os.getenv("KEALEX_DB_NAME")
    username = os.getenv("KEALEX_DB_USER")
    password = os.getenv("KEALEX_DB_PASSWORD")

    if host and database and username and password is not None:
        # Escapar caracteres especiais na senha usando quote_plus
        escaped_password = quote_plus(password)
        return make_url(
            f"mysql+pymysql://{username}:{escaped_password}@"
            f"{host}:{os.getenv('KEALEX_DB_PORT', '3306')}/{database}"
        )
```

## Caracteres Escapados

O `quote_plus()` converte caracteres especiais para URL-safe:
- `@` → `%40`
- `!` → `%21`
- `#` → `%23`
- `$` → `%24`
- `%` → `%25`
- `&` → `%26`
- etc.

## Variáveis do EasyPanel

As variáveis agora funcionam corretamente:
- `KEALEX_DB_HOST` ✅
- `KEALEX_DB_PORT` ✅
- `KEALEX_DB_NAME` ✅
- `KEALEX_DB_USER` ✅
- `KEALEX_DB_PASSWORD` ✅ (com caracteres especiais)

## Arquivos Modificados

- `app/main.py` - Atualizado para usar `quote_plus()` na construção da URL

## Teste

Para verificar se a conexão está funcionando:

```bash
curl http://localhost:8000/debug/db-status
```

Resposta esperada:
```json
{
  "status": "connected",
  "database_url": "mysql+pymysql://user@host:3306/database",
  "host": "srv1078.hstgr.io",
  "port": "3306",
  "database": "u549746795_kealex",
  "message": "Conexão com banco de dados estabelecida com sucesso"
}
```
