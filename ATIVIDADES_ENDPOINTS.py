# Adicionar ao app/main.py - Modelo e Endpoints de Atividade

# ── MODELO DE ATIVIDADE ────────────────────────────────────────────────────

class Atividade(Base):
    __tablename__ = "atividades"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    processo_id = Column(String(36), nullable=False)
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    tipo = Column(String(50), default="geral")  # geral, reuniao, ligacao, email, etc
    status = Column(String(50), default="pendente")  # pendente, concluida, cancelada
    prioridade = Column(String(20), default="normal")  # baixa, normal, alta, urgente
    data_vencimento = Column(DateTime, nullable=True)
    data_conclusao = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── SCHEMAS PYDANTIC ───────────────────────────────────────────────────────

class AtividadeIn(BaseModel):
    processoId: str
    titulo: str
    descricao: Optional[str] = None
    tipo: str = "geral"
    prioridade: str = "normal"
    dataVencimento: Optional[str] = None


class AtividadeUpdate(BaseModel):
    id: str
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    tipo: Optional[str] = None
    status: Optional[str] = None
    prioridade: Optional[str] = None
    dataVencimento: Optional[str] = None


# ── HELPER FUNCTIONS ───────────────────────────────────────────────────────

def _atividade_to_dict(a: Atividade) -> dict:
    return {
        "id": a.id,
        "tenantId": a.tenant_id,
        "userId": a.user_id,
        "processoId": a.processo_id,
        "titulo": a.titulo,
        "descricao": a.descricao,
        "tipo": a.tipo,
        "status": a.status,
        "prioridade": a.prioridade,
        "dataVencimento": a.data_vencimento.isoformat() if a.data_vencimento else None,
        "dataConclusao": a.data_conclusao.isoformat() if a.data_conclusao else None,
        "createdAt": a.created_at.isoformat(),
        "updatedAt": a.updated_at.isoformat(),
    }


# ── ENDPOINTS DE ATIVIDADE ─────────────────────────────────────────────────

@app.get("/k1/lex/atividades")
@app.get("/v1/lex/atividades")
def list_atividades(db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Lista todas as atividades do tenant"""
    tenant_id = payload.get("tenant_id")
    atividades = db.query(Atividade).filter_by(tenant_id=tenant_id).order_by(Atividade.created_at.desc()).all()
    return [_atividade_to_dict(a) for a in atividades]


@app.post("/k1/lex/atividades", status_code=201)
@app.post("/v1/lex/atividades", status_code=201)
def criar_atividade(body: AtividadeIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Cria uma nova atividade"""
    try:
        tenant_id = payload.get("tenant_id")
        
        # Validar se processo existe
        processo = db.query(Processo).filter_by(id=body.processoId, tenant_id=tenant_id).first()
        if not processo:
            raise HTTPException(404, "Processo não encontrado")
        
        atividade = Atividade(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=payload["sub"],
            processo_id=body.processoId,
            titulo=body.titulo,
            descricao=body.descricao,
            tipo=body.tipo,
            prioridade=body.prioridade,
            status="pendente",
            data_vencimento=datetime.fromisoformat(body.dataVencimento) if body.dataVencimento else None,
        )
        db.add(atividade)
        db.commit()
        db.refresh(atividade)
        
        return _atividade_to_dict(atividade)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Erro ao criar atividade: {str(e)}")


@app.post("/k1/lex/atividades/get")
@app.post("/v1/lex/atividades/get")
def get_atividade(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Obtém uma atividade específica"""
    try:
        atividade_id = body.get("id")
        if not atividade_id:
            raise HTTPException(400, "ID obrigatório")
        
        tenant_id = payload.get("tenant_id")
        atividade = db.query(Atividade).filter_by(id=atividade_id, tenant_id=tenant_id).first()
        if not atividade:
            raise HTTPException(404, "Atividade não encontrada")
        
        return _atividade_to_dict(atividade)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erro ao obter atividade: {str(e)}")


@app.post("/k1/lex/atividades/update")
@app.post("/v1/lex/atividades/update")
def update_atividade(body: AtividadeUpdate, db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Atualiza uma atividade"""
    try:
        tenant_id = payload.get("tenant_id")
        atividade = db.query(Atividade).filter_by(id=body.id, tenant_id=tenant_id).first()
        if not atividade:
            raise HTTPException(404, "Atividade não encontrada")
        
        # Atualizar campos
        if body.titulo is not None:
            atividade.titulo = body.titulo
        if body.descricao is not None:
            atividade.descricao = body.descricao
        if body.tipo is not None:
            atividade.tipo = body.tipo
        if body.status is not None:
            atividade.status = body.status
            if body.status == "concluida":
                atividade.data_conclusao = datetime.utcnow()
        if body.prioridade is not None:
            atividade.prioridade = body.prioridade
        if body.dataVencimento is not None:
            atividade.data_vencimento = datetime.fromisoformat(body.dataVencimento)
        
        atividade.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(atividade)
        
        return _atividade_to_dict(atividade)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Erro ao atualizar atividade: {str(e)}")


@app.post("/k1/lex/atividades/delete")
@app.post("/v1/lex/atividades/delete")
def delete_atividade(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Deleta uma atividade"""
    try:
        atividade_id = body.get("id")
        if not atividade_id:
            raise HTTPException(400, "ID obrigatório")
        
        tenant_id = payload.get("tenant_id")
        atividade = db.query(Atividade).filter_by(id=atividade_id, tenant_id=tenant_id).first()
        if not atividade:
            raise HTTPException(404, "Atividade não encontrada")
        
        db.delete(atividade)
        db.commit()
        
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Erro ao deletar atividade: {str(e)}")


@app.get("/k1/lex/atividades/processo/{processo_id}")
@app.get("/v1/lex/atividades/processo/{processo_id}")
def listar_atividades_por_processo(processo_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Lista atividades de um processo específico"""
    try:
        tenant_id = payload.get("tenant_id")
        
        # Validar se processo existe
        processo = db.query(Processo).filter_by(id=processo_id, tenant_id=tenant_id).first()
        if not processo:
            raise HTTPException(404, "Processo não encontrado")
        
        atividades = db.query(Atividade).filter_by(
            processo_id=processo_id,
            tenant_id=tenant_id
        ).order_by(Atividade.data_vencimento, Atividade.created_at.desc()).all()
        
        return [_atividade_to_dict(a) for a in atividades]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erro ao listar atividades: {str(e)}")


@app.post("/k1/lex/atividades/concluir")
@app.post("/v1/lex/atividades/concluir")
def concluir_atividade(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Marca uma atividade como concluída"""
    try:
        atividade_id = body.get("id")
        if not atividade_id:
            raise HTTPException(400, "ID obrigatório")
        
        tenant_id = payload.get("tenant_id")
        atividade = db.query(Atividade).filter_by(id=atividade_id, tenant_id=tenant_id).first()
        if not atividade:
            raise HTTPException(404, "Atividade não encontrada")
        
        atividade.status = "concluida"
        atividade.data_conclusao = datetime.utcnow()
        atividade.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(atividade)
        
        return _atividade_to_dict(atividade)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Erro ao concluir atividade: {str(e)}")


@app.get("/k1/lex/atividades/pendentes")
@app.get("/v1/lex/atividades/pendentes")
def listar_atividades_pendentes(db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Lista atividades pendentes do tenant"""
    try:
        tenant_id = payload.get("tenant_id")
        atividades = db.query(Atividade).filter_by(
            tenant_id=tenant_id,
            status="pendente"
        ).order_by(Atividade.prioridade.desc(), Atividade.data_vencimento).all()
        
        return [_atividade_to_dict(a) for a in atividades]
    except Exception as e:
        raise HTTPException(500, f"Erro ao listar atividades pendentes: {str(e)}")
