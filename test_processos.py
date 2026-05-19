#!/usr/bin/env python3
import requests
import json

# Fazer login para obter token
login_data = {
    "email": "admin@kealex.com",
    "senha": "admin123"
}

try:
    # Login
    print("=== TESTANDO LOGIN ===")
    response = requests.post("http://localhost:8000/auth/login", json=login_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        auth_data = response.json()
        token = auth_data["accessToken"]
        print(f"Token obtido: {token[:50]}...")
        print(f"Tenant ID: {auth_data['tenantId']}")
        
        # Testar endpoint de processos
        print("\n=== TESTANDO ENDPOINT PROCESSOS ===")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get("http://localhost:8000/processos", headers=headers)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            processos = response.json()
            print(f"Processos encontrados: {len(processos)}")
            for i, processo in enumerate(processos):
                print(f"  {i+1}. {processo['numero']} - {processo['titulo']}")
        else:
            print(f"Erro: {response.text}")
    else:
        print(f"Erro no login: {response.text}")

except Exception as e:
    print(f"Erro: {e}")