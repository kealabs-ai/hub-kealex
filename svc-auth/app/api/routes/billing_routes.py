from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os, hmac, uuid, httpx
from jose import jwt
from app.core.config import KEALEX_SECRET_KEY, ALGORITHM, TRIAL_DAYS
from app.infrastructure.database.models.auth_models import Usuario, Tenant, Escritorio, AsaasWebhookEvent
from app.infrastructure.database.session import get_db
from app.infrastructure.security.jwt_provider import verify_token
from app.application.use_cases.grant_subscription_period import grant_subscription_period
from app.api.schemas.billing_schema import CreditCardIn, HolderInfoIn, AssinarIn, AssinarOut, AssinarPixIn, AssinarPixOut
from app.core.normalization import digits

router = APIRouter()

KEALEX_ASAAS_API_KEY = os.getenv("KEALEX_ASAAS_API_KEY", "")
ASAAS_BASE    = os.getenv("KEALEX_ASAAS_BASE_URL", "").rstrip("/")
if not ASAAS_BASE:
    raise RuntimeError("KEALEX_ASAAS_BASE_URL precisa estar configurada no ambiente")

PLANOS = {
    "starter":      {"value": 197.00, "description": "Plano Starter"},
    "professional": {"value": 397.00, "description": "Plano Professional"},
}


def _build_asaas_card_payload(body: AssinarIn) -> dict:
    """Normaliza os dados de cartÃ£o e titular aceitos pelo Asaas."""
    holder = body.holderInfo
    card_number = digits(body.creditCard.number) or ""
    # O Sandbox do Asaas disponibiliza cartÃµes de teste que podem nÃ£o passar
    # na validaÃ§Ã£o Luhn (ex.: 4444 4444 4444 4444). A validaÃ§Ã£o final deve
    # ser feita pelo Asaas; aqui sÃ³ rejeitamos comprimentos impossÃ­veis.
    if not 13 <= len(card_number) <= 19:
        raise HTTPException(400, "NÃºmero do cartÃ£o invÃ¡lido. Confira os dÃ­gitos informados.")

    mobile_phone = digits(holder.mobilePhone)
    holder_info = {
        "name": holder.name,
        "email": holder.email,
        "cpfCnpj": digits(holder.cpfCnpj),
        "postalCode": digits(holder.postalCode),
        "addressNumber": holder.addressNumber,
        "addressComplement": holder.addressComplement,
        "phone": digits(holder.phone) or mobile_phone,
        # mobilePhone Ã© aceito pelo endpoint de assinatura do Asaas.
        "mobilePhone": mobile_phone,
    }

    return {
        "creditCard": {
            "holderName": body.creditCard.holderName,
            "number": card_number,
            "expiryMonth": body.creditCard.expiryMonth,
            "expiryYear": body.creditCard.expiryYear,
            "ccv": body.creditCard.ccv,
        },
        "creditCardHolderInfo": {
            key: value for key, value in holder_info.items()
            if value not in (None, "")
        },
        "remoteIp": body.remoteIp,
    }

def _build_asaas_subscription_payload(body: AssinarIn, plan_cfg: dict, next_due: str,
                                      value: float, cycle: str) -> dict:
    """Converte o payload interno para o formato de POST /v3/subscriptions."""
    return {
        "customer": body.asaasCustomerId,
        "billingType": "CREDIT_CARD",
        "value": value,
        "nextDueDate": next_due,
        "cycle": cycle,
        "description": plan_cfg["description"],
        **_build_asaas_card_payload(body),
    }

@router.post("/k1/lex/auth/assinar", response_model=AssinarOut)
def assinar(body: AssinarIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    plano_cfg = PLANOS.get(body.plano)
    if not plano_cfg:
        raise HTTPException(400, f"Plano invalido: {body.plano}. Use: {list(PLANOS.keys())}")

    tenant_id = payload.get("tenant_id")
    tenant = db.query(Tenant).filter_by(id=tenant_id).first()
    if not tenant:
        raise HTTPException(404, "Tenant nao encontrado")
    user = db.query(Usuario).filter_by(id=payload.get("sub"), tenant_id=tenant_id).first()
    if not user or (not user.ativo and payload.get("pre") is not True):
        raise HTTPException(403, "Sessao nao autorizada para contratar")
    if tenant.asaas_customer_id != body.asaasCustomerId:
        raise HTTPException(403, "Cliente Asaas nao vinculado a esta conta")
    periodicidade = body.periodicidade or "mensal"
    if periodicidade not in ("mensal", "trimestral"):
        raise HTTPException(400, "Periodicidade invalida. Use mensal ou trimestral.")
    if tenant.asaas_subscription_id and tenant.subscription_status == "active":
        raise HTTPException(409, "Ja existe uma assinatura vinculada a esta conta")

    meses = 3 if periodicidade == "trimestral" else 1
    desconto = plano_cfg["value"] * meses * 0.05 if periodicidade == "trimestral" else 0.0
    valor_total = round(plano_cfg["value"] * meses - desconto, 2)
    cycle = "QUARTERLY" if periodicidade == "trimestral" else "MONTHLY"

    # No checkout, a primeira cobranÃ§a deve ser tentada imediatamente pelo Asaas.
    # Para assinaturas com cartÃ£o, nextDueDate igual Ã  data atual solicita o
    # processamento da primeira cobranÃ§a no momento da criaÃ§Ã£o.
    now = datetime.utcnow()
    next_due = now.strftime("%Y-%m-%d")

    headers = {
        "access_token": KEALEX_ASAAS_API_KEY,
        "Content-Type": "application/json",
        "User-Agent": "Kealex/1.0.0",
    }

    # Se jÃ¡ existe uma assinatura pendente, substitui-a antes de criar outra.
    # A remoÃ§Ã£o pelo Asaas tambÃ©m remove cobranÃ§as pendentes e vencidas ligadas a ela.
    if tenant.asaas_subscription_id and tenant.subscription_status == "pending":
        previous_subscription_id = tenant.asaas_subscription_id
        try:
            payments_resp = httpx.get(
                f"{ASAAS_BASE}/payments",
                params={"subscription": previous_subscription_id, "limit": 100},
                headers=headers,
                timeout=15,
            )
            if payments_resp.status_code != 200:
                raise HTTPException(502, "Nao foi possivel verificar a assinatura pendente no Asaas.")

            payments = payments_resp.json().get("data", [])
            if any((payment.get("status") or "").upper() in {"CONFIRMED", "RECEIVED"} for payment in payments):
                tenant.subscription_status = "active"
                tenant.plano = tenant.subscription_plan or tenant.plano
                tenant.ativo = True
                tenant.updated_at = datetime.utcnow()
                db.query(Usuario).filter_by(tenant_id=tenant.id).update({"ativo": True})
                db.commit()
                raise HTTPException(409, "A assinatura anterior ja possui pagamento confirmado.")

            remove_resp = httpx.delete(
                f"{ASAAS_BASE}/subscriptions/{previous_subscription_id}",
                headers=headers,
                timeout=60,
            )
            if remove_resp.status_code not in (200, 204, 404):
                detail = remove_resp.json().get("errors", remove_resp.text)
                raise HTTPException(502, f"Nao foi possivel substituir a assinatura pendente: {detail}")
            logging.info(
                "[ASSINAR] Assinatura pendente removida para substituicao tenant=%s subscription=%s",
                tenant.id,
                previous_subscription_id,
            )
        except httpx.TimeoutException:
            raise HTTPException(504, "Timeout ao substituir a assinatura pendente no Asaas.")

    # Retry the existing overdue invoice instead of creating a second subscription.
    if tenant.subscription_status == "past_due" and tenant.asaas_subscription_id:
        if body.plano != tenant.subscription_plan:
            raise HTTPException(409, "Para regularizar a cobranÃ§a, selecione o plano atual da conta.")
        try:
            payments_response = httpx.get(
                f"{ASAAS_BASE}/payments",
                params={"subscription": tenant.asaas_subscription_id, "limit": 100},
                headers=headers,
                timeout=15,
            )
            if payments_response.status_code != 200:
                raise HTTPException(502, "Nao foi possivel consultar a cobranca vencida no Asaas.")
            overdue_payments = [
                payment for payment in payments_response.json().get("data", [])
                if payment.get("status") == "OVERDUE"
            ]
            if not overdue_payments:
                raise HTTPException(409, "Nao encontramos uma cobranca vencida para regularizar no Asaas.")
            overdue_payments.sort(key=lambda payment: payment.get("dueDate", ""), reverse=True)
            payment = overdue_payments[0]
            payment_resp = httpx.post(
                f"{ASAAS_BASE}/payments/{payment['id']}/payWithCreditCard",
                json=_build_asaas_card_payload(body),
                headers=headers,
                timeout=60,
            )
            if payment_resp.status_code != 200:
                detail = payment_resp.json().get("errors", payment_resp.text)
                raise HTTPException(422, f"Asaas recusou a regularizacao: {detail}")
            payment_data = payment_resp.json()
        except httpx.TimeoutException:
            raise HTTPException(504, "Timeout ao regularizar a cobranca no Asaas.")

        payment_status = (payment_data.get("status") or "").upper()
        if payment_status in ("CONFIRMED", "RECEIVED"):
            tenant.subscription_cycle = tenant.subscription_cycle or cycle
            grant_subscription_period(tenant, payment_data.get("id"), body.plano)
            db.query(Usuario).filter_by(tenant_id=tenant.id).update({"ativo": True})
        elif payment_status in ("PENDING", "AWAITING_RISK_ANALYSIS"):
            tenant.subscription_status = "pending"
        tenant.next_due_date = payment_data.get("dueDate") or tenant.next_due_date
        tenant.updated_at = datetime.utcnow()
        db.commit()
        return AssinarOut(
            subscriptionId=tenant.asaas_subscription_id,
            plano=tenant.subscription_plan or body.plano,
            periodicidade=periodicidade,
            status=payment_status or "PENDING",
            nextDueDate=tenant.next_due_date or next_due,
            value=float(payment_data.get("value") or valor_total),
            valorMensal=plano_cfg["value"],
            desconto=desconto,
        )

    # Create the recurring subscription first so every payment, including an
    # asynchronous card confirmation, is associated with the webhook's subscription ID.
    try:
        sub_resp = httpx.post(
            f"{ASAAS_BASE}/subscriptions",
            json=_build_asaas_subscription_payload(body, plano_cfg, next_due, valor_total, cycle),
            headers=headers,
            timeout=60,
        )
        if sub_resp.status_code not in (200, 201):
            detail = sub_resp.json().get("errors", sub_resp.text)
            raise HTTPException(422, f"Asaas recusou a assinatura: {detail}")
        subscription = sub_resp.json()
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao criar assinatura no Asaas.")

    subscription_id = subscription.get("id")
    if not subscription_id:
        raise HTTPException(502, "Asaas criou uma resposta sem identificador de assinatura.")

    # Persiste o ID antes de consultar a cobranÃ§a para que um webhook imediato
    # jÃ¡ encontre a assinatura vinculada ao tenant.
    tenant.asaas_subscription_id = subscription_id
    tenant.subscription_plan = body.plano
    tenant.subscription_cycle = cycle
    tenant.subscription_status = "pending"
    tenant.next_due_date = subscription.get("nextDueDate") or next_due
    tenant.updated_at = datetime.utcnow()
    db.commit()

    # A resposta de /subscriptions representa a recorrÃªncia, nÃ£o o pagamento.
    # Busca a primeira cobranÃ§a para retornar ao front o resultado conhecido.
    payment_status = "PENDING"
    payment_value = valor_total
    payment_due_date = tenant.next_due_date
    try:
        payments_resp = httpx.get(
            f"{ASAAS_BASE}/payments",
            params={"subscription": subscription_id, "limit": 100},
            headers=headers,
            timeout=15,
        )
        if payments_resp.status_code == 200:
            payments = payments_resp.json().get("data", [])
            if payments:
                payments.sort(key=lambda payment: payment.get("dueDate", ""), reverse=True)
                payment = payments[0]
                payment_status = (payment.get("status") or "PENDING").upper()
                payment_value = float(payment.get("value") or valor_total)
                payment_due_date = payment.get("dueDate") or payment_due_date
                if payment_status in ("CONFIRMED", "RECEIVED"):
                    grant_subscription_period(tenant, payment.get("id"), body.plano)
                    db.query(Usuario).filter_by(tenant_id=tenant.id).update({"ativo": True})
                elif payment_status == "OVERDUE":
                    tenant.subscription_status = "past_due"
                    tenant.ativo = False
                tenant.next_due_date = payment_due_date
                tenant.updated_at = datetime.utcnow()
                db.commit()
        else:
            logging.warning(
                "[ASSINAR] Asaas criou subscription=%s, mas consulta inicial da cobranÃ§a retornou HTTP %s",
                subscription_id,
                payments_resp.status_code,
            )
    except (httpx.TimeoutException, ValueError) as exc:
        # A assinatura jÃ¡ foi criada; nÃ£o repetir nem falhar a contrataÃ§Ã£o por
        # uma consulta de status. O webhook atualizarÃ¡ o estado posteriormente.
        logging.warning(
            "[ASSINAR] Asaas criou subscription=%s, mas nÃ£o foi possÃ­vel consultar o pagamento: %s",
            subscription_id,
            type(exc).__name__,
        )

    return AssinarOut(
        subscriptionId=subscription_id,
        plano=body.plano,
        periodicidade=periodicidade,
        status=payment_status,
        nextDueDate=payment_due_date,
        value=payment_value,
        valorMensal=plano_cfg["value"],
        desconto=desconto,
    )



@router.post("/k1/lex/auth/assinar-pix", response_model=AssinarPixOut)
def assinar_pix(body: AssinarPixIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    plano_cfg = PLANOS.get(body.plano)
    if not plano_cfg:
        raise HTTPException(400, f"Plano invalido: {body.plano}")
    periodicidade = body.periodicidade or "mensal"
    if periodicidade not in ("mensal", "trimestral"):
        raise HTTPException(400, "Periodicidade invalida. Use mensal ou trimestral.")

    tenant_id = payload.get("tenant_id")
    tenant = db.query(Tenant).filter_by(id=tenant_id).first()
    if not tenant:
        raise HTTPException(404, "Tenant nao encontrado")
    if tenant.asaas_customer_id != body.asaasCustomerId:
        raise HTTPException(403, "Cliente Asaas nao vinculado a esta conta")
    if tenant.asaas_subscription_id and tenant.subscription_status in ("pending", "active"):
        raise HTTPException(409, "Ja existe uma assinatura vinculada a esta conta")

    meses = 3 if periodicidade == "trimestral" else 1
    desconto = plano_cfg["value"] * meses * 0.05 if periodicidade == "trimestral" else 0.0
    valor_total = round(plano_cfg["value"] * meses - desconto, 2)
    cycle = "QUARTERLY" if periodicidade == "trimestral" else "MONTHLY"
    now = datetime.utcnow()
    if tenant.plano == "trial" and tenant.trial_expires_at and tenant.trial_expires_at > now:
        next_due = tenant.trial_expires_at.strftime("%Y-%m-%d")
    else:
        next_due = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    headers = {"access_token": KEALEX_ASAAS_API_KEY, "Content-Type": "application/json", "User-Agent": "Kealex/1.0.0"}

    if tenant.subscription_status == "past_due" and tenant.asaas_subscription_id:
        if body.plano != tenant.subscription_plan:
            raise HTTPException(409, "Para regularizar a cobranca, selecione o plano atual da conta.")
        try:
            payments_resp = httpx.get(
                f"{ASAAS_BASE}/payments",
                params={"subscription": tenant.asaas_subscription_id, "limit": 100},
                headers=headers,
                timeout=15,
            )
            if payments_resp.status_code != 200:
                raise HTTPException(502, "Nao foi possivel consultar a cobranca vencida no Asaas.")
            overdue_payments = [
                payment for payment in payments_resp.json().get("data", [])
                if payment.get("status") == "OVERDUE" and payment.get("billingType") == "PIX"
            ]
            if not overdue_payments:
                raise HTTPException(409, "Esta cobranca vencida nao aceita PIX. Escolha cartao de credito.")
            overdue_payments.sort(key=lambda payment: payment.get("dueDate", ""), reverse=True)
            payment_id = overdue_payments[0]["id"]
            due_date = overdue_payments[0].get("dueDate") or next_due
            qr_resp = httpx.get(
                f"{ASAAS_BASE}/payments/{payment_id}/pixQrCode",
                headers=headers,
                timeout=15,
            )
            if qr_resp.status_code != 200:
                raise HTTPException(422, f"Nao foi possivel recuperar o PIX vencido: {qr_resp.text}")
            qr_data = qr_resp.json()
        except httpx.TimeoutException:
            raise HTTPException(504, "Timeout ao consultar a cobranca PIX no Asaas.")

        return AssinarPixOut(
            subscriptionId=tenant.asaas_subscription_id,
            plano=tenant.subscription_plan or body.plano,
            periodicidade=periodicidade,
            status="PENDING",
            nextDueDate=due_date,
            value=float(overdue_payments[0].get("value") or valor_total),
            valorMensal=plano_cfg["value"],
            desconto=desconto,
            pixQrCode=qr_data.get("encodedImage", ""),
            pixKey=qr_data.get("payload", ""),
            pixExpiresAt=qr_data.get("expirationDate") or (now + timedelta(hours=24)).isoformat(),
        )

    # 1. Criar assinatura PIX
    try:
        resp = httpx.post(
            f"{ASAAS_BASE}/subscriptions",
            json={
                "customer":    body.asaasCustomerId,
                "billingType": "PIX",
                "nextDueDate": next_due,
                "value":       valor_total,
                "cycle":       cycle,
                "description": plano_cfg["description"],
            },
            headers=headers,
            timeout=20,
        )
        if resp.status_code not in (200, 201):
            raise HTTPException(422, f"Asaas recusou: {resp.json().get('errors', resp.text)}")
        sub = resp.json()
        subscription_id = sub.get("id")
        if not subscription_id:
            raise HTTPException(502, "Asaas criou uma resposta sem identificador de assinatura.")
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao conectar com Asaas")

    tenant.asaas_subscription_id = subscription_id
    tenant.subscription_plan = body.plano
    tenant.subscription_cycle = cycle
    tenant.subscription_status = "pending"
    tenant.next_due_date = next_due
    tenant.ativo = True
    tenant.updated_at = datetime.utcnow()
    db.commit()

    # 2. Buscar o pagamento gerado para a assinatura
    try:
        resp = httpx.get(
            f"{ASAAS_BASE}/payments",
            params={"subscription": subscription_id, "limit": 1},
            headers=headers,
            timeout=15,
        )
        if resp.status_code != 200:
            raise HTTPException(502, "Nao foi possivel consultar a primeira cobranca PIX no Asaas.")
        payments = resp.json().get("data", [])
        if not payments:
            raise HTTPException(422, "Nenhum pagamento gerado para a assinatura PIX")
        payment_id = payments[0]["id"]
        due_date = payments[0].get("dueDate", next_due)
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao buscar pagamento")

    # 3. Buscar QR Code PIX do pagamento
    try:
        resp = httpx.get(
            f"{ASAAS_BASE}/payments/{payment_id}/pixQrCode",
            headers=headers,
            timeout=15,
        )
        if resp.status_code != 200:
            raise HTTPException(422, f"Erro ao obter QR Code PIX: {resp.text}")
        qr_data = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao obter QR Code PIX")

    tenant.next_due_date = due_date
    tenant.updated_at = datetime.utcnow()
    db.commit()

    expires_at = (now + timedelta(hours=24)).isoformat()

    return AssinarPixOut(
        subscriptionId=subscription_id,
        plano=body.plano,
        periodicidade=periodicidade,
        status="PENDING",
        nextDueDate=due_date,
        value=valor_total,
        valorMensal=plano_cfg["value"],
        desconto=desconto,
        pixQrCode=qr_data.get("encodedImage", ""),
        pixKey=qr_data.get("payload", ""),
        pixExpiresAt=qr_data.get("expirationDate") or expires_at,
    )


@router.post("/k1/lex/auth/criar-cliente-asaas")
def criar_cliente_asaas(body: HolderInfoIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Cria ou recupera um customer no Asaas para o usuario autenticado."""
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant:
        raise HTTPException(404, "Tenant nao encontrado")
    customer_data = {
        "name": body.name,
        "email": body.email,
        "cpfCnpj": digits(body.cpfCnpj),
        "phone": digits(body.phone),
        "mobilePhone": digits(body.mobilePhone),
        "postalCode": digits(body.postalCode),
        "addressNumber": body.addressNumber,
        "complement": body.addressComplement,
        "address": body.address,
        "province": body.neighborhood,
        "city": body.city,
    }
    customer_data = {key: value for key, value in customer_data.items() if value not in (None, "")}
    try:
        if tenant.asaas_customer_id:
            resp = httpx.put(
                f"{ASAAS_BASE}/customers/{tenant.asaas_customer_id}",
                json=customer_data,
                headers={"access_token": KEALEX_ASAAS_API_KEY, "Content-Type": "application/json"},
                timeout=15,
            )
        else:
            resp = httpx.post(
                f"{ASAAS_BASE}/customers",
                json=customer_data,
                headers={"access_token": KEALEX_ASAAS_API_KEY, "Content-Type": "application/json"},
                timeout=15,
            )
        if resp.status_code not in (200, 201):
            detail = resp.json().get("errors", resp.text)
            raise HTTPException(422, f"Asaas recusou os dados do titular: {detail}")
        customer_id = tenant.asaas_customer_id or resp.json().get("id")
        tenant.asaas_customer_id = customer_id
        tenant.billing_name = body.name
        tenant.billing_email = body.email
        tenant.billing_cpf_cnpj = digits(body.cpfCnpj)
        tenant.billing_phone = digits(body.phone)
        tenant.billing_mobile_phone = digits(body.mobilePhone)
        tenant.billing_postal_code = digits(body.postalCode)
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


@router.get("/k1/lex/auth/billing-profile")
def billing_profile(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant:
        raise HTTPException(404, "Tenant nao encontrado")

    cpf_cnpj = tenant.billing_cpf_cnpj
    phone = tenant.billing_phone
    mobile_phone = tenant.billing_mobile_phone
    if tenant.asaas_customer_id and (not cpf_cnpj or (not phone and not mobile_phone)):
        try:
            response = httpx.get(
                f"{ASAAS_BASE}/customers/{tenant.asaas_customer_id}",
                headers={"access_token": KEALEX_ASAAS_API_KEY},
                timeout=10,
            )
            if response.status_code == 200:
                customer = response.json()
                cpf_cnpj = cpf_cnpj or customer.get("cpfCnpj")
                phone = phone or customer.get("phone")
                mobile_phone = mobile_phone or customer.get("mobilePhone")
                tenant.billing_cpf_cnpj = cpf_cnpj
                tenant.billing_phone = phone
                tenant.billing_mobile_phone = mobile_phone
                db.commit()
        except httpx.TimeoutException:
            pass

    return {
        "name": tenant.billing_name or "",
        "email": tenant.billing_email or "",
        "cpfCnpj": cpf_cnpj or "",
        "phone": phone or "",
        "mobilePhone": mobile_phone or "",
        "postalCode": tenant.billing_postal_code or "",
        "address": tenant.billing_address or "",
        "addressNumber": tenant.billing_address_number or "",
        "addressComplement": tenant.billing_complement or "",
        "neighborhood": tenant.billing_neighborhood or "",
        "city": tenant.billing_city or "",
        "state": tenant.billing_state or "",
    }


@router.post("/k1/lex/auth/asaas-webhook")
async def asaas_webhook(
    request: Request,
    db: Session = Depends(get_db),
    access_token: str | None = Header(default=None, alias="asaas-access-token"),
):
    expected = os.getenv("KEALEX_ASAAS_WEBHOOK_TOKEN", "")
    if not expected or not access_token or not hmac.compare_digest(access_token, expected):
        raise HTTPException(401, "Webhook nao autenticado")

    event = await request.json()
    event_id = event.get("id")
    event_name = event.get("event", "")
    if not event_id:
        raise HTTPException(400, "Evento sem identificador")
    if db.get(AsaasWebhookEvent, event_id):
        return {"ok": True, "duplicate": True}

    # Registra todo evento vÃ¡lido, mesmo quando nÃ£o estiver associado a uma
    # assinatura (por exemplo, eventos de pagamentos avulsos).
    db.add(AsaasWebhookEvent(id=event_id, event=event_name))

    payment = event.get("payment") or {}
    subscription_id = payment.get("subscription") or (event.get("subscription") or {}).get("id")
    if not subscription_id:
        db.commit()
        return {"ok": True, "ignored": True}
    tenant = db.query(Tenant).filter_by(asaas_subscription_id=subscription_id).with_for_update().first()
    if tenant:
        if event_name in ("PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"):
            grant_subscription_period(tenant, payment.get("id"))
            tenant.next_due_date = payment.get("dueDate") or tenant.next_due_date
            db.query(Usuario).filter_by(tenant_id=tenant.id).update({"ativo": True})
        elif event_name == "PAYMENT_OVERDUE":
            tenant.subscription_status = "past_due"
            tenant.ativo = False
        elif event_name == "SUBSCRIPTION_DELETED":
            tenant.subscription_status = "canceled"
            tenant.ativo = False
        tenant.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "ignored": tenant is None}

@router.get("/k1/lex/auth/billing-status")
def billing_status(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant:
        raise HTTPException(404, "Tenant nao encontrado")
    now = datetime.utcnow()
    if tenant.plano == "trial":
        trial_expired = tenant.trial_expires_at and tenant.trial_expires_at <= now
        if tenant.subscription_status == "pending" and trial_expired:
            status = "pending"
        else:
            status = "trial_expired" if trial_expired else "trial"
    elif tenant.plano in ("starter", "professional", "enterprise"):
        subscription_status = (tenant.subscription_status or "").lower()
        if subscription_status in ("pending", "past_due", "canceled"):
            status = subscription_status
        elif (tenant.subscription_expires_at and now >= tenant.subscription_expires_at):
            status = "past_due"
        elif tenant.ativo and subscription_status == "active":
            status = "active"
        else:
            status = "inactive"
    else:
        status = "inactive"
    return {
        "plano": tenant.plano,
        "status": status,
        "subscriptionStatus": tenant.subscription_status,
        "nextDueDate": tenant.next_due_date,
        "trialExpiresAt": tenant.trial_expires_at.isoformat() if tenant.trial_expires_at else None,
        "subscriptionExpiresAt": tenant.subscription_expires_at.isoformat() + "Z" if tenant.subscription_expires_at else None,
    }


@router.post("/k1/lex/auth/assinatura/reativar", response_model=AssinarOut)
def reativar_assinatura(body: dict = {}, db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Verifica o status do pagamento pendente no Asaas e atualiza o tenant."""
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant or not tenant.asaas_subscription_id:
        raise HTTPException(404, "Nenhuma assinatura encontrada")
    if tenant.subscription_status == "active":
        raise HTTPException(409, "Assinatura ja esta ativa")

    headers = {"access_token": KEALEX_ASAAS_API_KEY, "Content-Type": "application/json", "User-Agent": "Kealex/1.0.0"}
    try:
        resp = httpx.get(
            f"{ASAAS_BASE}/payments",
            params={"subscription": tenant.asaas_subscription_id, "limit": 1},
            headers=headers,
            timeout=15,
        )
        payments = resp.json().get("data", []) if resp.status_code == 200 else []
        if not payments:
            raise HTTPException(422, "Nenhum pagamento encontrado para reativar")
        payment = payments[0]
        payment_status = (payment.get("status") or "").upper()
        plano_cfg = PLANOS.get(tenant.subscription_plan or tenant.plano, {})
        now = datetime.utcnow()
        if payment_status in ("CONFIRMED", "RECEIVED"):
            grant_subscription_period(tenant, payment.get("id"))
            db.query(Usuario).filter_by(tenant_id=tenant.id).update({"ativo": True})
            db.commit()
        return AssinarOut(
            subscriptionId=tenant.asaas_subscription_id,
            plano=tenant.subscription_plan or tenant.plano,
            periodicidade="mensal",
            status=payment_status or "PENDING",
            nextDueDate=payment.get("dueDate") or now.strftime("%Y-%m-%d"),
            value=payment.get("value") or plano_cfg.get("value", 0),
            valorMensal=plano_cfg.get("value", 0),
            desconto=0.0,
        )
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao conectar com Asaas")


@router.get("/k1/lex/auth/assinatura")
def get_assinatura(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant or not tenant.asaas_subscription_id:
        raise HTTPException(404, "Nenhuma assinatura encontrada")

    periodicidade = "mensal"
    pix_qr_code = None
    pix_key = None
    pix_expires_at = None
    billing_type = None

    # Tenta buscar detalhes atualizados no Asaas
    try:
        headers = {"access_token": KEALEX_ASAAS_API_KEY, "User-Agent": "Kealex/1.0.0"}
        resp = httpx.get(
            f"{ASAAS_BASE}/subscriptions/{tenant.asaas_subscription_id}",
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            sub = resp.json()
            cycle = (sub.get("cycle") or "").upper()
            periodicidade = "trimestral" if cycle == "QUARTERLY" else "mensal"

        # Se pendente, tenta buscar QR Code do pagamento mais recente
        if tenant.subscription_status in ("pending", "past_due"):
            pay_resp = httpx.get(
                f"{ASAAS_BASE}/payments",
                params={"subscription": tenant.asaas_subscription_id, "limit": 100},
                headers=headers,
                timeout=10,
            )
            if pay_resp.status_code == 200:
                payments = [
                    payment for payment in pay_resp.json().get("data", [])
                    if payment.get("status") in ("PENDING", "OVERDUE")
                ]
                if payments:
                    payments.sort(key=lambda payment: payment.get("dueDate", ""), reverse=True)
                    payment = payments[0]
                    billing_type = (payment.get("billingType") or "").upper()
                    if billing_type == "PIX":
                        qr_resp = httpx.get(
                            f"{ASAAS_BASE}/payments/{payment['id']}/pixQrCode",
                            headers=headers,
                            timeout=10,
                        )
                        if qr_resp.status_code == 200:
                            qr = qr_resp.json()
                            pix_qr_code = qr.get("encodedImage")
                            pix_key = qr.get("payload")
                            pix_expires_at = qr.get("expirationDate")
    except httpx.TimeoutException:
        pass

    plano_cfg = PLANOS.get(tenant.subscription_plan or tenant.plano, {})
    return {
        "subscriptionId": tenant.asaas_subscription_id,
        "plano": tenant.subscription_plan or tenant.plano,
        "periodicidade": periodicidade,
        "valor": plano_cfg.get("value", 0),
        "status": tenant.subscription_status or "inactive",
        "subscriptionStatus": tenant.subscription_status or "pending",
        "billingType": billing_type,
        "createdAt": tenant.created_at.isoformat() if tenant.created_at else None,
        "nextDueDate": tenant.next_due_date,
        "pixQrCode": pix_qr_code,
        "pixKey": pix_key,
        "pixExpiresAt": pix_expires_at,
    }

