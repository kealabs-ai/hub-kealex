#!/usr/bin/env python3
import secrets
import string

def generate_secret_key(length=50):
    """Gera uma SECRET_KEY segura para uso em produção"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

if __name__ == "__main__":
    secret_key = generate_secret_key()
    print(f"SECRET_KEY={secret_key}")
    print(f"\nCopie esta chave e configure no Jenkins como credencial 'kealex-secret-key'")