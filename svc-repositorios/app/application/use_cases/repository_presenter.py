import json


def repository_to_dict(repository):
    return {
        "id": repository.id,
        "tenantId": repository.tenant_id,
        "userId": repository.user_id,
        "nome": repository.nome,
        "tipo": repository.tipo,
        "status": repository.status,
        "url": repository.url,
        "caminhoLocal": repository.caminho_local,
        "gdriveFolder": repository.gdrive_folder_id,
        "descricao": repository.descricao,
        "metadados": json.loads(repository.metadados) if repository.metadados else {},
        "createdAt": repository.created_at.isoformat(),
        "updatedAt": repository.updated_at.isoformat(),
    }


def file_to_dict(file):
    return {
        "id": file.id,
        "tenantId": file.tenant_id,
        "repositorioId": file.repositorio_id,
        "nome": file.nome,
        "caminho": file.caminho,
        "tipoMime": file.tipo_mime,
        "tamanhoBytes": file.tamanho_bytes,
        "hashArquivo": file.hash_arquivo,
        "metadados": json.loads(file.metadados) if file.metadados else {},
        "createdAt": file.created_at.isoformat(),
        "updatedAt": file.updated_at.isoformat(),
    }
