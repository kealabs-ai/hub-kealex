from app.infrastructure.database.models.office_model import Escritorio

def _to_dict(e: Escritorio, usuarios_ativos: int = 0, advogados_ativos: int = 0, acesso_configurado: bool = False):
    return {
        "id": e.id, "tenantId": e.tenant_id, "nome": e.nome, "cnpj": e.cnpj,
        "endereco": e.endereco, "telefone": e.telefone, "email": e.email, "ativo": e.ativo,
        "limiteAdvogados": e.limite_advogados, "codigo": e.codigo,
        "acessoConfigurado": acesso_configurado,
        "usuariosAtivos": usuarios_ativos, "advogadosAtivos": advogados_ativos,
        "createdAt": e.created_at.isoformat(), "updatedAt": e.updated_at.isoformat()
    }

