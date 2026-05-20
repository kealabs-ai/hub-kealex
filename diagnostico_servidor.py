#!/usr/bin/env python3
"""
Script de diagnóstico para verificar o status do servidor Kealex
"""

import requests
import json
from urllib.parse import urlparse

def test_url(url, description):
    print(f"\n[TESTE] {description}")
    print(f"URL: {url}")
    print("-" * 50)
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        # Tentar parsear como JSON
        try:
            data = response.json()
            print(f"Response JSON: {json.dumps(data, indent=2, ensure_ascii=False)}")
        except:
            print(f"Response Text: {response.text[:500]}...")
            
    except requests.exceptions.ConnectionError:
        print("[ERRO] Erro de conexao - servidor nao esta respondendo")
    except requests.exceptions.Timeout:
        print("[TIMEOUT] Timeout - servidor demorou para responder")
    except Exception as e:
        print(f"[ERRO] Erro: {e}")

def test_login(base_url):
    print(f"\n[LOGIN] TESTANDO LOGIN")
    print("-" * 50)
    
    login_url = f"{base_url}/v1/lex/auth/login"
    login_data = {
        "email": "admin@kealex.com",
        "senha": "admin123"
    }
    
    try:
        response = requests.post(
            login_url, 
            json=login_data, 
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"URL: {login_url}")
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        try:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        except:
            print(f"Response Text: {response.text}")
            
    except Exception as e:
        print(f"[ERRO] Erro no login: {e}")

def main():
    print("DIAGNOSTICO DO SERVIDOR KEALEX")
    print("=" * 60)
    
    # URLs para testar
    base_url = "https://srv1023256.hstgr.cloud"
    
    # Teste 1: Raiz do servidor
    test_url(base_url, "Testando raiz do servidor")
    
    # Teste 2: Endpoint antigo (sem v1/lex)
    test_url(f"{base_url}/auth/login", "Testando endpoint antigo /auth/login")
    
    # Teste 3: Novo endpoint
    test_url(f"{base_url}/v1/lex/auth/login", "Testando novo endpoint /v1/lex/auth/login")
    
    # Teste 4: Verificar se é FastAPI
    test_url(f"{base_url}/docs", "Testando documentação FastAPI (/docs)")
    test_url(f"{base_url}/openapi.json", "Testando OpenAPI schema")
    
    # Teste 5: Outros endpoints possíveis
    test_url(f"{base_url}/health", "Testando health check")
    test_url(f"{base_url}/status", "Testando status")
    test_url(f"{base_url}/api", "Testando /api")
    test_url(f"{base_url}/v1", "Testando /v1")
    
    # Teste 6: Login
    test_login(base_url)
    
    print(f"\n[RESUMO] RESUMO DO DIAGNOSTICO")
    print("=" * 60)
    print("1. Verifique se o docker-compose está rodando")
    print("2. Verifique se o nginx está configurado corretamente")
    print("3. Verifique se os serviços FastAPI estão funcionando")
    print("4. O erro 'Route POST:/api/errors/not-found' sugere outro framework")
    print("5. Pode haver um proxy reverso ou load balancer na frente")

if __name__ == "__main__":
    main()