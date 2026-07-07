#!/usr/bin/env python3
"""
Script de teste para validar endpoints de processos com fases
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
TOKEN = "seu-token-jwt-aqui"  # Substituir com token real

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_create_processo():
    """Testa criação de processo com fases padrão"""
    print("\n=== Teste 1: Criar Processo ===")
    payload = {
        "numero": "0001234-56.2024.8.26.0100",
        "titulo": "Ação Civil - Teste",
        "descricao": "Processo de teste para validar fases",
        "clienteId": "cliente-uuid-aqui",
        "vara": "1ª Vara Cível",
        "tribunal": "TJSP"
    }
    
    response = requests.post(
        f"{BASE_URL}/k1/lex/processos",
        json=payload,
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    if response.status_code == 201:
        print("✅ Processo criado com sucesso!")
        print(f"   - ID: {data['id']}")
        print(f"   - Fases criadas: {len(data.get('fases', []))}")
        print(f"   - Fase atual: {data.get('faseAtual', 0)}")
        return data['id']
    else:
        print("❌ Erro ao criar processo")
        return None

def test_list_processos():
    """Testa listagem de processos com fases"""
    print("\n=== Teste 2: Listar Processos ===")
    response = requests.get(
        f"{BASE_URL}/k1/lex/processos",
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if response.status_code == 200:
        print(f"✅ {len(data)} processo(s) encontrado(s)")
        for p in data[:1]:  # Mostrar apenas o primeiro
            print(f"\n   Processo: {p['numero']}")
            print(f"   Fases: {len(p.get('fases', []))}")
            for i, fase in enumerate(p.get('fases', [])):
                print(f"     {i+1}. {fase['label']} - Status: {fase['status']}")
    else:
        print("❌ Erro ao listar processos")
    
    return data[0]['id'] if data else None

def test_avancar_fase(processo_id):
    """Testa avanço de fase"""
    print(f"\n=== Teste 3: Avançar Fase ===")
    print(f"Processo ID: {processo_id}")
    
    payload = {
        "id": processo_id,
        "novaFase": 1
    }
    
    response = requests.post(
        f"{BASE_URL}/k1/lex/processos/avancar-fase",
        json=payload,
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if response.status_code == 200:
        print("✅ Fase avançada com sucesso!")
        print(f"   - Fase atual: {data.get('faseAtual', 0)}")
        print(f"   - Fases:")
        for i, fase in enumerate(data.get('fases', [])):
            status_icon = "✓" if fase['status'] == 'concluida' else "●" if fase['status'] == 'ativa' else "○"
            print(f"     {status_icon} {fase['label']} - {fase['status']}")
    else:
        print("❌ Erro ao avançar fase")
        print(json.dumps(data, indent=2, ensure_ascii=False))

def test_get_processo(processo_id):
    """Testa obtenção de processo específico"""
    print(f"\n=== Teste 4: Obter Processo ===")
    
    payload = {"id": processo_id}
    
    response = requests.post(
        f"{BASE_URL}/k1/lex/processos/get",
        json=payload,
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if response.status_code == 200:
        print("✅ Processo obtido com sucesso!")
        print(f"   - Número: {data['numero']}")
        print(f"   - Título: {data['titulo']}")
        print(f"   - Fase atual: {data.get('faseAtual', 0)}")
        print(f"   - Total de fases: {len(data.get('fases', []))}")
    else:
        print("❌ Erro ao obter processo")

def main():
    print("=" * 60)
    print("TESTES DE ENDPOINTS - PROCESSOS COM FASES")
    print("=" * 60)
    
    # Teste 1: Criar processo
    processo_id = test_create_processo()
    
    if processo_id:
        # Teste 2: Listar processos
        test_list_processos()
        
        # Teste 3: Obter processo específico
        test_get_processo(processo_id)
        
        # Teste 4: Avançar fase
        test_avancar_fase(processo_id)
        
        # Teste 5: Avançar novamente
        print(f"\n=== Teste 5: Avançar Fase Novamente ===")
        test_avancar_fase(processo_id)
    
    print("\n" + "=" * 60)
    print("TESTES CONCLUÍDOS")
    print("=" * 60)

if __name__ == "__main__":
    main()
