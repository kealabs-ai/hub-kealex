import httpx

from fastapi import APIRouter

from app.legacy_context import (
    ALGORITHM,
    ASAAS_BASE,
    AsaasWebhookEvent,
    AssinarIn,
    AssinarOut,
    AssinarPixIn,
    AssinarPixOut,
    AssinarPreviewOut,
    AuthUser,
    Depends,
    HTTPException,
    Header,
    HolderInfoIn,
    KEALEX_ASAAS_API_KEY,
    KEALEX_SECRET_KEY,
    LoginIn,
    PLANOS,
    PreRegisterIn,
    PreRegisterOut,
    RegisterIn,
    Request,
    RoleEnum,
    Session,
    TRIAL_DAYS,
    Tenant,
    Usuario,
    _calcular_valor,
    _digits,
    _hash,
    _json,
    _make_token,
    _verify,
    _verify_webhook_token,
    datetime,
    get_db,
    jwt,
    logging,
    timedelta,
    uuid,
    verify_identity_token,
    verify_token,
)

router = APIRouter()


@router.post("/k1/lex/auth/pre-register", response_model=PreRegisterOut, status_code=201)
def pre_register(body: PreRegisterIn, db: Session = Depends(get_db)):
    if len(body.senha) < 6:
        raise HTTPException(400, "Senha deve ter no minimo 6 caracteres")
    if db.query(Usuario).filter_by(email=body.email).first():
        raise HTTPException(409, "E-mail ja cadastrado.")
    slug = body.email.split("@")[0].lower().replace(".", "-")[:80]
    base_slug, counter = slug, 1
    while db.query(Tenant).filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"; counter += 1
    now = datetime.utcnow()
    tenant = Tenant(nome=body.nome, slug=slug, plano="trial",
                    trial_started_at=now, trial_expires_at=now + timedelta(days=TRIAL_DAYS), ativo=True)
    db.add(tenant); db.flush()
    user = Usuario(tenant_id=tenant.id, nome=body.nome, email=body.email,
                   senha_hash=_hash(body.senha), role=RoleEnum.advogado, ativo=True)
    db.add(user); db.commit(); db.refresh(user)
    token = jwt.encode(
        {"sub": user.id, "role": user.role, "tenant_id": tenant.id,
         "exp": datetime.utcnow() + timedelta(hours=2), "pre": True},
        KEALEX_SECRET_KEY, ALGORITHM)
    return PreRegisterOut(userId=user.id, tenantId=tenant.id, token=token)


@router.post("/k1/lex/auth/criar-cliente-asaas")
def criar_cliente_asaas(body: HolderInfoIn, db: Session = Depends(get_db), payload=Depends(verify_identity_token)):
    if not ASAAS_BASE:
        raise HTTPException(503, "Integracao Asaas nao configurada")
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant: raise HTTPException(404, "Tenant nao encontrado")
    customer_data = {k: v for k, v in {
        "name": body.name, "email": body.email, "cpfCnpj": _digits(body.cpfCnpj),
        "phone": _digits(body.phone), "mobilePhone": _digits(body.mobilePhone),
        "postalCode": _digits(body.postalCode), "addressNumber": body.addressNumber,
        "complement": body.addressComplement, "address": body.address,
        "province": body.neighborhood, "city": body.city,
    }.items() if v not in (None, "")}
    headers = {"access_token": KEALEX_ASAAS_API_KEY, "Content-Type": "application/json", "User-Agent": "Kealex/1.0.0"}
    try:
        if tenant.asaas_customer_id:
            resp = httpx.put(f"{ASAAS_BASE}/customers/{tenant.asaas_customer_id}", json=customer_data, headers=headers, timeout=15)
        else:
            resp = httpx.post(f"{ASAAS_BASE}/customers", json=customer_data, headers=headers, timeout=15)
        if resp.status_code not in (200, 201):
            raise HTTPException(422, f"Asaas recusou: {resp.json().get('errors', resp.text)}")
        customer_id = tenant.asaas_customer_id or resp.json().get("id")
        tenant.asaas_customer_id = customer_id
        tenant.billing_name = body.name
        tenant.billing_email = body.email
        tenant.billing_cpf_cnpj = _digits(body.cpfCnpj)
        tenant.billing_phone = _digits(body.phone)
        tenant.billing_mobile_phone = _digits(body.mobilePhone)
        tenant.billing_postal_code = _digits(body.postalCode)
        tenant.billing_address = body.address
        tenant.billing_address_number = body.addressNumber
        tenant.billing_complement = body.addressComplement
        tenant.billing_neighborhood = body.neighborhood
        tenant.billing_city = body.city
        tenant.billing_state = body.state
        db.commit()
        return {"customerId": customer_id}
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao conectar com Asaas")


@router.post("/k1/lex/auth/assinar/preview", response_model=AssinarPreviewOut)
def assinar_preview(body: AssinarIn, db: Session = Depends(get_db), payload=Depends(verify_identity_token)):
    plano_cfg = PLANOS.get(body.plano)
    if not plano_cfg: raise HTTPException(400, f"Plano invalido: {body.plano}")
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant: raise HTTPException(404, "Tenant nao encontrado")
    if tenant.asaas_customer_id != body.asaasCustomerId:
        raise HTTPException(403, "Cliente Asaas nao vinculado a esta conta")
    valor_mensal = plano_cfg["value"]
    valor_total, _ = _calcular_valor(valor_mensal, body.periodicidade)
    desconto = round(valor_mensal * (3 if body.periodicidade == "trimestral" else 1) - valor_total, 2)
    now = datetime.utcnow()
    next_due = tenant.trial_expires_at.strftime("%Y-%m-%d") if tenant.plano == "trial" and tenant.trial_expires_at and tenant.trial_expires_at > now else (now + timedelta(days=1)).strftime("%Y-%m-%d")
    cartao_final = body.creditCard.number[-4:] if body.creditCard.number else "****"
    mensagem = (
        f"Voce esta contratando o {plano_cfg['description']} no ciclo {'trimestral com 5% de desconto' if body.periodicidade == 'trimestral' else 'mensal'}. "
        f"O valor de R$ {valor_total:.2f} sera cobrado em {next_due} no cartao terminado em {cartao_final}. "
        f"Clique em Confirmar para finalizar a contratacao."
    )
    return AssinarPreviewOut(
        plano=body.plano, descricaoPlano=plano_cfg["description"],
        periodicidade=body.periodicidade, valorMensal=valor_mensal,
        valorTotal=valor_total, desconto=desconto, nextDueDate=next_due,
        titular=body.holderInfo.name, email=body.holderInfo.email,
        cpfCnpj=body.holderInfo.cpfCnpj[-4:].rjust(len(body.holderInfo.cpfCnpj), "*"),
        cartaoFinal=cartao_final, mensagem=mensagem,
    )


@router.post("/k1/lex/auth/assinar", response_model=AssinarOut)
def assinar(body: AssinarIn, db: Session = Depends(get_db), payload=Depends(verify_identity_token)):
    if not ASAAS_BASE:
        raise HTTPException(503, "Integracao Asaas nao configurada")
    plano_cfg = PLANOS.get(body.plano)
    if not plano_cfg: raise HTTPException(400, f"Plano invalido: {body.plano}")
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant: raise HTTPException(404, "Tenant nao encontrado")
    if tenant.asaas_customer_id != body.asaasCustomerId:
        raise HTTPException(403, "Cliente Asaas nao vinculado a esta conta")
    if tenant.asaas_subscription_id:
        _h = {"access_token": KEALEX_ASAAS_API_KEY, "Content-Type": "application/json", "User-Agent": "Kealex/1.0.0"}
        try:
            _r = httpx.get(f"{ASAAS_BASE}/subscriptions/{tenant.asaas_subscription_id}", headers=_h, timeout=10)
            asaas_status = _r.json().get("status", "") if _r.status_code == 200 else ""
        except Exception:
            asaas_status = ""
        if asaas_status == "ACTIVE":
            raise HTTPException(409, "Ja existe uma assinatura ativa vinculada a esta conta")
        # Cancela assinatura pendente/inativa no Asaas antes de criar nova
        try:
            httpx.delete(f"{ASAAS_BASE}/subscriptions/{tenant.asaas_subscription_id}", headers=_h, timeout=10)
        except Exception:
            pass
        logging.warning("[ASSINAR] Assinatura anterior cancelada asaas_status=%s tenant=%s",
                        asaas_status, tenant.id)
        tenant.asaas_subscription_id = None
        tenant.subscription_status = "trialing"
        db.commit()
    valor_mensal = plano_cfg["value"]
    valor_total, installment_count = _calcular_valor(valor_mensal, body.periodicidade)
    desconto = round(valor_mensal * (3 if body.periodicidade == "trimestral" else 1) - valor_total, 2)
    now = datetime.utcnow()
    next_due = tenant.trial_expires_at.strftime("%Y-%m-%d") if tenant.plano == "trial" and tenant.trial_expires_at and tenant.trial_expires_at > now else (now + timedelta(days=1)).strftime("%Y-%m-%d")
    headers = {"access_token": KEALEX_ASAAS_API_KEY, "Content-Type": "application/json", "User-Agent": "Kealex/1.0.0"}
    subscription_payload = {
        "customer": body.asaasCustomerId, "billingType": "CREDIT_CARD",
        "nextDueDate": next_due, "value": valor_total, "cycle": "MONTHLY",
        "description": f"{plano_cfg['description']} ({'Trimestral' if body.periodicidade == 'trimestral' else 'Mensal'})",
        "creditCard": {"holderName": body.creditCard.holderName, "number": body.creditCard.number,
                       "expiryMonth": body.creditCard.expiryMonth, "expiryYear": body.creditCard.expiryYear, "ccv": body.creditCard.ccv},
        "creditCardHolderInfo": {k: v for k, v in {
            "name": body.holderInfo.name, "email": body.holderInfo.email,
            "cpfCnpj": _digits(body.holderInfo.cpfCnpj), "postalCode": _digits(body.holderInfo.postalCode),
            "addressNumber": body.holderInfo.addressNumber,
            "addressComplement": body.holderInfo.addressComplement,
            "phone": _digits(body.holderInfo.phone) or _digits(body.holderInfo.mobilePhone),
        }.items() if v not in (None, "")},
        "remoteIp": body.remoteIp,
    }
    if body.periodicidade == "trimestral":
        subscription_payload["installmentCount"] = 3
        subscription_payload["installmentValue"] = round(valor_total / 3, 2)
    try:
        resp = httpx.post(f"{ASAAS_BASE}/subscriptions", headers=headers, timeout=20, json=subscription_payload)
        if resp.status_code not in (200, 201):
            raise HTTPException(422, f"Asaas recusou: {resp.json().get('errors', resp.text)}")
        data = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao conectar com Asaas")
    # Salva como pending e aguarda webhook para ativar — não polling de status
    tenant.asaas_subscription_id = data.get("id")
    tenant.subscription_plan = body.plano
    tenant.subscription_status = "pending"
    tenant.next_due_date = data.get("nextDueDate", next_due)
    tenant.updated_at = datetime.utcnow()
    db.commit()
    return AssinarOut(subscriptionId=data.get("id", ""), plano=body.plano, periodicidade=body.periodicidade,
                      status="PENDING",
                      nextDueDate=data.get("nextDueDate", next_due),
                      value=valor_total, valorMensal=valor_mensal, desconto=desconto)


@router.post("/k1/lex/auth/assinar-pix", response_model=AssinarPixOut)
def assinar_pix(body: AssinarPixIn, db: Session = Depends(get_db), payload=Depends(verify_identity_token)):
    if not ASAAS_BASE:
        raise HTTPException(503, "Integracao Asaas nao configurada")
    plano_cfg = PLANOS.get(body.plano)
    if not plano_cfg: raise HTTPException(400, f"Plano invalido: {body.plano}")
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant: raise HTTPException(404, "Tenant nao encontrado")
    if tenant.asaas_customer_id != body.asaasCustomerId:
        raise HTTPException(403, "Cliente Asaas nao vinculado a esta conta")
    if tenant.asaas_subscription_id and tenant.subscription_status in ("active", "past_due"):
        raise HTTPException(409, "Ja existe uma assinatura ativa vinculada a esta conta")
    valor_mensal = plano_cfg["value"]
    valor_total, installment_count = _calcular_valor(valor_mensal, body.periodicidade)
    desconto = round(valor_mensal * (3 if body.periodicidade == "trimestral" else 1) - valor_total, 2)
    now = datetime.utcnow()
    next_due = tenant.trial_expires_at.strftime("%Y-%m-%d") if tenant.plano == "trial" and tenant.trial_expires_at and tenant.trial_expires_at > now else (now + timedelta(days=1)).strftime("%Y-%m-%d")
    headers = {"access_token": KEALEX_ASAAS_API_KEY, "Content-Type": "application/json", "User-Agent": "Kealex/1.0.0"}
    pix_payload = {
        "customer": body.asaasCustomerId, "billingType": "PIX",
        "nextDueDate": next_due, "value": valor_total, "cycle": "MONTHLY",
        "description": f"{plano_cfg['description']} ({'Trimestral' if body.periodicidade == 'trimestral' else 'Mensal'})",
    }
    if body.periodicidade == "trimestral":
        pix_payload["installmentCount"] = 3
        pix_payload["installmentValue"] = round(valor_total / 3, 2)
    try:
        # 1. Criar assinatura PIX
        resp = httpx.post(f"{ASAAS_BASE}/subscriptions", headers=headers, timeout=20, json=pix_payload)
        if resp.status_code not in (200, 201):
            raise HTTPException(422, f"Asaas recusou: {resp.json().get('errors', resp.text)}")
        subscription_id = resp.json()["id"]
        # 2. Buscar pagamento gerado
        resp = httpx.get(f"{ASAAS_BASE}/payments", headers=headers, timeout=15,
                         params={"subscription": subscription_id, "limit": 1})
        payments = resp.json().get("data", [])
        if not payments: raise HTTPException(422, "Nenhum pagamento gerado para a assinatura PIX")
        payment_id = payments[0]["id"]
        due_date = payments[0].get("dueDate", next_due)
        # 3. Buscar QR Code
        resp = httpx.get(f"{ASAAS_BASE}/payments/{payment_id}/pixQrCode", headers=headers, timeout=15)
        if resp.status_code != 200:
            raise HTTPException(422, f"Erro ao obter QR Code PIX: {resp.text}")
        qr_data = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao conectar com Asaas")
    tenant.asaas_subscription_id = subscription_id
    tenant.subscription_plan = body.plano
    tenant.subscription_status = "pending"
    tenant.next_due_date = due_date
    tenant.updated_at = datetime.utcnow()
    if not tenant.ativo:
        tenant.ativo = True
        db.query(Usuario).filter_by(tenant_id=tenant.id).update({"ativo": True})
    db.commit()
    return AssinarPixOut(
        subscriptionId=subscription_id, plano=body.plano, periodicidade=body.periodicidade,
        status="PENDING", nextDueDate=due_date,
        value=valor_total, valorMensal=valor_mensal, desconto=desconto,
        pixQrCode=qr_data.get("encodedImage", ""),
        pixKey=qr_data.get("payload", ""),
        pixExpiresAt=qr_data.get("expirationDate") or (now + timedelta(hours=24)).isoformat(),
    )


@router.post("/k1/lex/auth/asaas-webhook")
async def asaas_webhook(
    request: Request,
    db: Session = Depends(get_db),
    access_token: str | None = Header(default=None, alias="asaas-access-token"),
):
    if not _verify_webhook_token(access_token):
        logging.warning("[WEBHOOK] Token invalido recebido: %s", access_token)
        raise HTTPException(401, "Webhook nao autenticado")

    raw_body = await request.body()
    try:
        event = _json.loads(raw_body)
    except _json.JSONDecodeError:
        raise HTTPException(400, "Payload invalido")

    event_id   = event.get("id") or str(uuid.uuid4())
    event_name = event.get("event", "")

    # ── Idempotência: ignora eventos já processados ──────────────────────────
    if db.get(AsaasWebhookEvent, event_id):
        logging.info("[WEBHOOK] Evento duplicado ignorado: %s", event_id)
        return {"ok": True, "duplicated": True}

    db.add(AsaasWebhookEvent(
        id=event_id,
        event=event_name,
    ))

    # ── Extrai subscription_id ───────────────────────────────────────────────
    payment      = event.get("payment") or {}
    subscription = event.get("subscription") or {}
    subscription_id = (
        payment.get("subscription")
        or subscription.get("id")
        or payment.get("subscriptionId")
    )

    if not subscription_id:
        logging.info("[WEBHOOK] Evento sem subscription_id ignorado: %s", event_name)
        db.commit()
        return {"ok": True, "ignored": True}

    tenant = db.query(Tenant).filter_by(asaas_subscription_id=subscription_id).first()
    if not tenant:
        logging.warning("[WEBHOOK] Tenant nao encontrado para subscription: %s", subscription_id)
        db.commit()
        return {"ok": True, "tenant_not_found": True}

    logging.info("[WEBHOOK] Processando evento=%s subscription=%s tenant=%s",
                 event_name, subscription_id, tenant.id)

    # ── Transições de estado ─────────────────────────────────────────────────
    if event_name in ("PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"):
        tenant.subscription_status = "active"
        tenant.plano = tenant.subscription_plan or tenant.plano
        tenant.ativo = True
        if payment.get("dueDate"):
            tenant.next_due_date = payment["dueDate"]
        db.query(Usuario).filter_by(tenant_id=tenant.id).update({"ativo": True})

    elif event_name == "PAYMENT_OVERDUE":
        tenant.subscription_status = "past_due"

    elif event_name in ("SUBSCRIPTION_DELETED", "PAYMENT_DELETED"):
        tenant.subscription_status = "canceled"
        tenant.ativo = False
        db.query(Usuario).filter_by(tenant_id=tenant.id).update({"ativo": False})

    elif event_name == "PAYMENT_REFUNDED":
        tenant.subscription_status = "inactive"

    elif event_name == "SUBSCRIPTION_UPDATED":
        if subscription.get("nextDueDate"):
            tenant.next_due_date = subscription["nextDueDate"]

    tenant.updated_at = datetime.utcnow()
    db.commit()
    logging.info("[WEBHOOK] Tenant %s atualizado: status=%s plano=%s",
                 tenant.id, tenant.subscription_status, tenant.plano)
    return {"ok": True}


@router.get("/k1/lex/auth/billing-status")
def billing_status(db: Session = Depends(get_db), payload=Depends(verify_identity_token)):
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant: raise HTTPException(404, "Tenant nao encontrado")
    now = datetime.utcnow()
    if not tenant.ativo:
        status = "inactive"
    elif tenant.plano == "trial":
        status = "trial_expired" if tenant.trial_expires_at and tenant.trial_expires_at <= now else "trial"
    elif tenant.plano in ("starter", "professional", "enterprise"):
        status = tenant.subscription_status or "inactive"
    else:
        status = "inactive"
    return {"plano": tenant.plano, "status": status, "subscriptionStatus": tenant.subscription_status,
            "nextDueDate": tenant.next_due_date,
            "trialExpiresAt": tenant.trial_expires_at.isoformat() if tenant.trial_expires_at else None}


@router.get("/k1/lex/auth/billing-profile")
def billing_profile_v2(db: Session = Depends(get_db), payload=Depends(verify_identity_token)):
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant: raise HTTPException(404, "Tenant nao encontrado")
    return {
        "name": tenant.billing_name or "",
        "email": tenant.billing_email or "",
        "cpfCnpj": tenant.billing_cpf_cnpj or "",
        "phone": tenant.billing_phone or "",
        "mobilePhone": tenant.billing_mobile_phone or "",
        "postalCode": tenant.billing_postal_code or "",
        "address": tenant.billing_address or "",
        "addressNumber": tenant.billing_address_number or "",
        "addressComplement": tenant.billing_complement or "",
        "neighborhood": tenant.billing_neighborhood or "",
        "city": tenant.billing_city or "",
        "state": tenant.billing_state or "",
    }


@router.patch("/k1/lex/auth/billing-profile")
def update_billing_profile(body: HolderInfoIn, db: Session = Depends(get_db), payload=Depends(verify_identity_token)):
    """Atualiza dados do titular sem criar novo registro."""
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant: raise HTTPException(404, "Tenant nao encontrado")
    if body.name: tenant.billing_name = body.name
    if body.email: tenant.billing_email = body.email
    if body.cpfCnpj: tenant.billing_cpf_cnpj = _digits(body.cpfCnpj)
    if body.phone: tenant.billing_phone = _digits(body.phone)
    if body.mobilePhone: tenant.billing_mobile_phone = _digits(body.mobilePhone)
    if body.postalCode: tenant.billing_postal_code = _digits(body.postalCode)
    if body.address: tenant.billing_address = body.address
    if body.addressNumber: tenant.billing_address_number = body.addressNumber
    if body.addressComplement is not None: tenant.billing_complement = body.addressComplement
    if body.neighborhood: tenant.billing_neighborhood = body.neighborhood
    if body.city: tenant.billing_city = body.city
    if body.state: tenant.billing_state = body.state
    tenant.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.post("/auth/login", response_model=AuthUser)
@router.post("/k1/lex/auth/login", response_model=AuthUser)
def login(body: LoginIn, db: Session = Depends(get_db)):
    try:
        user = db.query(Usuario).filter_by(email=body.email, ativo=True).first()
        if not user or not _verify(body.senha, user.senha_hash):
            raise HTTPException(401, "Credenciais inválidas")
        tenant = db.query(Tenant).filter_by(id=user.tenant_id).first()
        return AuthUser(
            id=user.id,
            nome=user.nome,
            email=user.email,
            role=user.role,
            tenantId=user.tenant_id,
            accessToken=_make_token(user),
            plano=tenant.plano if tenant else "trial",
            subscriptionStatus=tenant.subscription_status if tenant else None,
            trialStartedAt=tenant.trial_started_at.isoformat() if tenant and tenant.trial_started_at else None,
            trialExpiresAt=tenant.trial_expires_at.isoformat() if tenant and tenant.trial_expires_at else None,
            subscriptionExpiresAt=tenant.subscription_expires_at.isoformat() + "Z" if tenant and tenant.subscription_expires_at else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[LOGIN_ERROR] {type(e).__name__}: {str(e)}")
        import traceback; traceback.print_exc()
        raise HTTPException(500, f"Erro no login: {str(e)}")


@router.post("/k1/lex/auth/register", response_model=AuthUser, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    cpf_cnpj = "".join(filter(str.isdigit, body.cpfCnpj or ""))
    if len(cpf_cnpj) not in (11, 14):
        raise HTTPException(400, "Informe um CPF ou CNPJ válido.")

    if db.query(Usuario).filter_by(email=body.email).first():
        raise HTTPException(409, "E-mail já cadastrado. Acesse /entrar para fazer login.")

    now  = datetime.utcnow()
    slug = body.email.split("@")[0].lower().replace(".", "-")[:80]
    base_slug, counter = slug, 1
    while db.query(Tenant).filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    tenant = Tenant(
        nome=body.nome,
        slug=slug,
        plano="trial",
        trial_started_at=now,
        trial_expires_at=now + timedelta(days=TRIAL_DAYS),
        email=body.email,
        whatsapp=body.whatsapp,
        billing_cpf_cnpj=cpf_cnpj,
        billing_mobile_phone="".join(filter(str.isdigit, body.whatsapp or "")),
        perfil=body.perfil,
    )
    db.add(tenant)
    db.flush()

    senha_temp = str(uuid.uuid4())[:8]
    user = Usuario(
        tenant_id=tenant.id,
        nome=body.nome,
        email=body.email,
        senha_hash=_hash(body.senha if body.senha else senha_temp),
        role=RoleEnum.advogado,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.refresh(tenant)

    print(f"[REGISTER] novo trial: {body.email} | tenant={tenant.id} | expires={tenant.trial_expires_at}")

    return AuthUser(
        id=user.id,
        nome=user.nome,
        email=user.email,
        role=user.role,
        tenantId=tenant.id,
        accessToken=_make_token(user),
        plano=tenant.plano,
        subscriptionStatus=tenant.subscription_status,
        trialStartedAt=tenant.trial_started_at.isoformat(),
        trialExpiresAt=tenant.trial_expires_at.isoformat(),
        subscriptionExpiresAt=tenant.subscription_expires_at.isoformat() + "Z" if tenant.subscription_expires_at else None,
    )


@router.get("/auth/me")
@router.get("/k1/lex/auth/me")
def me(payload=Depends(verify_token)):
    return payload
