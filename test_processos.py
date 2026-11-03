#!/usr/bin/env python3
import os
import requests
import json

# Fazer login para obter token
login_data = {
    "email": os.getenv("KEALEX_LOGIN_EMAIL"),
    "senha": os.getenv("KEALEX_LOGIN_PASSWORD")
}

if not all(login_data.values()):
    raise SystemExit("Configure KEALEX_LOGIN_EMAIL e KEALEX_LOGIN_PASSWORD para executar este script.")

try:
    # Login
    print("=== TESTANDO LOGIN ===")
    response = requests.post("http://localhost:8000/v1/lex/auth/login", json=login_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        auth_data = response.json()
        token = auth_data["accessToken"]
        print(f"Tenant ID: {auth_data['tenantId']}")
        
        # Testar endpoint de processos
        print("\n=== TESTANDO ENDPOINT PROCESSOS ===")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get("http://localhost:8000/v1/lex/processos", headers=headers)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            processos = response.json()
            print(f"Processos encontrados: {len(processos)}")
            for i, processo in enumerate(processos):
                print(f"  {i+1}. {processo['numero']} - {processo['titulo']}")
        else:
            print(f"Erro: {response.text}")
            
        # Testar endpoint de usuários
        print("\n=== TESTANDO ENDPOINT USUÁRIOS ===")
        response = requests.get("http://localhost:8000/v1/lex/usuarios", headers=headers)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            usuarios = response.json()
            print(f"Usuários encontrados: {len(usuarios)}")
        else:
            print(f"Erro: {response.text}")
            
    else:
        print(f"Erro no login: {response.text}")

except Exception as e:
    print(f"Erro: {e}")
