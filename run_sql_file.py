"""Execute SQL scripts using KEALEX_DATABASE_URL from the backend .env."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
database_url = os.getenv("KEALEX_DATABASE_URL")
if not database_url:
    raise SystemExit("KEALEX_DATABASE_URL is missing; configure it in the backend .env")
if len(sys.argv) != 2:
    raise SystemExit("Usage: python run_sql_file.py path/to/migration.sql")
sql_path = (ROOT / sys.argv[1]).resolve()
if ROOT not in sql_path.parents:
    raise SystemExit("SQL file must be inside the backend repository")
source = sql_path.read_text(encoding="utf-8-sig")

def statements(sql: str):
    result, current = [], []
    quote = None
    escaped = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < len(sql) else ""
        if quote is None and ch == "-" and nxt == "-":
            while i < len(sql) and sql[i] not in "\r\n": i += 1
            continue
        if quote is None and ch == "#":
            while i < len(sql) and sql[i] not in "\r\n": i += 1
            continue
        if quote:
            current.append(ch)
            if escaped: escaped = False
            elif ch == "\\": escaped = True
            elif ch == quote: quote = None
        elif ch in ("'", '"', "`"):
            quote = ch; current.append(ch)
        elif ch == ";":
            statement = "".join(current).strip()
            if statement: result.append(statement)
            current = []
        else: current.append(ch)
        i += 1
    tail = "".join(current).strip()
    if tail: result.append(tail)
    return result

engine = create_engine(database_url, pool_pre_ping=True)
with engine.begin() as connection:
    for statement in statements(source):
        result = connection.exec_driver_sql(statement)
        if result.returns_rows:
            for row in result: print(tuple(row))
print(f"Applied {sql_path.name} using backend .env configuration.")