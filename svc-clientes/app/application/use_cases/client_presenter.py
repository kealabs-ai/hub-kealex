from app.infrastructure.database.models.client_model import Cliente

def client_to_dict(c: Cliente):
    return {
        "id": c.id, "tenantId": c.tenant_id, "advogadoId": c.advogado_id,
        "nome": c.nome, "email": c.email, "telefone": c.telefone,
        "cpfCnpj": c.cpf_cnpj, "cep": getattr(c, "cep", None), "endereco": c.endereco,
        "cidade": getattr(c, "cidade", None), "estado": getattr(c, "estado", None),
        "rg": getattr(c, "rg", None), "orgaoExpedidor": getattr(c, "orgao_expedidor", None),
        "nacionalidade": getattr(c, "nacionalidade", None), "estadoCivil": getattr(c, "estado_civil", None),
        "profissao": getattr(c, "profissao", None), "dataNascimento": getattr(c, "data_nascimento", None),
        "razaoSocial": getattr(c, "razao_social", None), "nomeFantasia": getattr(c, "nome_fantasia", None),
        "inscricaoEstadual": getattr(c, "inscricao_estadual", None),
        "inscricaoMunicipal": getattr(c, "inscricao_municipal", None),
        "representanteLegal": getattr(c, "representante_legal", None), "whatsapp": getattr(c, "whatsapp", None),
        "observacoes": c.observacoes,
        "createdAt": c.created_at.isoformat(), "updatedAt": c.updated_at.isoformat(),
    }
