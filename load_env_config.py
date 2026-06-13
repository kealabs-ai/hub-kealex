#!/usr/bin/env python3
"""
Script para carregar variáveis de ambiente do Easypanel e exibir credenciais do banco
"""
import os
from dotenv import load_dotenv

# Carregar arquivo .env
load_dotenv()

print("=" * 80)
print("VARIÁVEIS DE AMBIENTE - CONFIGURAÇÃO DO BANCO DE DADOS")
print("=" * 80)
print()

# Variáveis de banco de dados
db_vars = {
    "DATABASE_URL": "URL de conexão do banco",
    "MYSQL_HOST": "Host do MySQL",
    "MYSQL_PORT": "Porta do MySQL",
    "MYSQL_DATABASE": "Nome do banco de dados",
    "MYSQL_USER": "Usuário do MySQL",
    "MYSQL_PASSWORD": "Senha do MySQL",
    "MYSQL_ROOT_PASSWORD": "Senha root do MySQL",
}

# Variáveis de configuração
config_vars = {
    "SECRET_KEY": "Chave secreta",
    "ENVIRONMENT": "Ambiente (dev/prod)",
    "DEBUG": "Modo debug",
}

# Variáveis de serviço
service_vars = {
    "SERVICE_NAME": "Nome do serviço",
    "SERVICE_PORT": "Porta do serviço",
}

print("📦 CONFIGURAÇÃO DO BANCO DE DADOS:")
print("-" * 80)
for key, description in db_vars.items():
    value = os.environ.get(key, "NÃO DEFINIDO")
    # Mascarar senha
    if "PASSWORD" in key and value != "NÃO DEFINIDO":
        value = "*" * len(value)
    print(f"  {key:<25} = {value:<30} ({description})")

print()
print("⚙️  CONFIGURAÇÃO GERAL:")
print("-" * 80)
for key, description in config_vars.items():
    value = os.environ.get(key, "NÃO DEFINIDO")
    print(f"  {key:<25} = {value:<30} ({description})")

print()
print("🔧 VARIÁVEIS DE SERVIÇO:")
print("-" * 80)
for key, description in service_vars.items():
    value = os.environ.get(key, "NÃO DEFINIDO")
    print(f"  {key:<25} = {value:<30} ({description})")

print()
print("📋 TODAS AS VARIÁVEIS DE AMBIENTE:")
print("-" * 80)
for key, value in sorted(os.environ.items()):
    # Mascarar valores sensíveis
    if any(s in key.upper() for s in ["PASSWORD", "SECRET", "KEY", "TOKEN", "API"]):
        value = "*" * len(value) if value else "VAZIO"
    print(f"  {key:<40} = {value}")

print()
print("=" * 80)
print("✅ Leitura de variáveis concluída!")
print("=" * 80)
