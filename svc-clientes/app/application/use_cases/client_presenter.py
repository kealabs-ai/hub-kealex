from app.infrastructure.database.models.client_model import Cliente

def client_to_dict(c: Cliente):
    return {
        "id": c.id, "tenantId": c.tenant_id, "advogadoId": c.advogado_id,
        "nome": c.nome, "email": c.email, "telefone": c.telefone,
        "cpfCnpj": c.cpf_cnpj, "endereco": c.endereco, "observacoes": c.observacoes,
        "createdAt": c.created_at.isoformat(), "updatedAt": c.updated_at.isoformat(),
    }
