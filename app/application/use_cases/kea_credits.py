import uuid
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

import httpx
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import ASAAS_BASE, KEALEX_ASAAS_API_KEY
from app.infrastructure.database.models import KeaCreditsTransaction, KeaCreditsWallet, Tenant


CREDIT_PACKAGES = {
    "essencial": {"name": "Essencial", "credits": 100, "price_cents": 1000},
    "escritorio": {"name": "Escritório", "credits": 300, "price_cents": 3000},
    "pro": {"name": "Pro", "credits": 600, "price_cents": 6000},
}
CREDIT_COSTS = {"receita-federal": 10}
PAID_EVENTS = {"PAYMENT_RECEIVED"}
REFUND_EVENTS = {"PAYMENT_REFUNDED", "PAYMENT_RECEIVED_IN_CASH_UNDONE"}
ASAA_HEADERS = {
    "access_token": KEALEX_ASAAS_API_KEY,
    "Content-Type": "application/json",
    "User-Agent": "Kealex/1.0.0",
}


def _wallet(db: Session, tenant_id: str, lock: bool = False) -> KeaCreditsWallet:
    query = db.query(KeaCreditsWallet).filter_by(organizacao_id=tenant_id)
    if lock:
        query = query.with_for_update()
    wallet = query.first()
    if wallet:
        return wallet

    try:
        with db.begin_nested():
            wallet = KeaCreditsWallet(id=str(uuid.uuid4()), organizacao_id=tenant_id, saldo_creditos=0)
            db.add(wallet)
            db.flush()
        return wallet
    except IntegrityError:
        query = db.query(KeaCreditsWallet).filter_by(organizacao_id=tenant_id)
        if lock:
            query = query.with_for_update()
        wallet = query.first()
        if not wallet:
            raise
        return wallet


def wallet_balance(db: Session, tenant_id: str) -> int:
    wallet = _wallet(db, tenant_id)
    db.commit()
    return wallet.saldo_creditos


def reserve_service_credits(db: Session, tenant_id: str, user_id: str, service_id: str, reference: str) -> int:
    credits = CREDIT_COSTS.get(service_id)
    if credits is None:
        raise HTTPException(422, "Serviço sem custo de KeaCredits configurado")

    existing = db.query(KeaCreditsTransaction).filter_by(organizacao_id=tenant_id, chave_idempotencia=reference).first()
    if existing:
        if existing.status in {"RESERVADO", "CONFIRMADO"}:
            return existing.saldo_depois or 0
        raise HTTPException(409, "Esta consulta já foi processada")

    wallet = _wallet(db, tenant_id, lock=True)
    if wallet.saldo_creditos < credits:
        raise HTTPException(402, "Saldo de KeaCredits insuficiente. Recarregue a carteira para continuar.")

    previous = wallet.saldo_creditos
    wallet.saldo_creditos -= credits
    wallet.atualizado_em = datetime.utcnow()
    db.add(KeaCreditsTransaction(
        id=str(uuid.uuid4()), organizacao_id=tenant_id, usuario_id=user_id,
        tipo="CONSUMO", status="RESERVADO", quantidade_creditos=-credits,
        saldo_antes=previous, saldo_depois=wallet.saldo_creditos,
        chave_idempotencia=reference, pacote_id=service_id,
        descricao=f"Consulta externa: {service_id}", criado_em=datetime.utcnow(),
    ))
    db.flush()
    return wallet.saldo_creditos


def confirm_service_credits(db: Session, tenant_id: str, reference: str) -> None:
    transaction = db.query(KeaCreditsTransaction).filter_by(
        organizacao_id=tenant_id, chave_idempotencia=reference,
    ).with_for_update().first()
    if transaction and transaction.status == "RESERVADO":
        transaction.status = "CONFIRMADO"
        transaction.confirmado_em = datetime.utcnow()


def refund_service_credits(db: Session, tenant_id: str, user_id: str, reference: str) -> None:
    transaction = db.query(KeaCreditsTransaction).filter_by(
        organizacao_id=tenant_id, chave_idempotencia=reference,
    ).with_for_update().first()
    if not transaction or transaction.status != "RESERVADO":
        return

    wallet = _wallet(db, tenant_id, lock=True)
    credits = abs(transaction.quantidade_creditos)
    previous = wallet.saldo_creditos
    wallet.saldo_creditos += credits
    wallet.atualizado_em = datetime.utcnow()
    transaction.status = "ESTORNADO"
    transaction.confirmado_em = datetime.utcnow()
    db.add(KeaCreditsTransaction(
        id=str(uuid.uuid4()), organizacao_id=tenant_id, usuario_id=user_id,
        tipo="ESTORNO", status="CONFIRMADO", quantidade_creditos=credits,
        saldo_antes=previous, saldo_depois=wallet.saldo_creditos,
        chave_idempotencia=f"estorno:{reference}", pacote_id=transaction.pacote_id,
        descricao="Estorno de consulta externa não concluída", criado_em=datetime.utcnow(),
        confirmado_em=datetime.utcnow(),
    ))


def _centavos(value) -> int | None:
    try:
        return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except Exception:
        return None


def _pix_payload(transaction: KeaCreditsTransaction, package: dict) -> dict:
    status = {
        "PENDENTE": "PENDING",
        "CONFIRMADO": "RECEIVED",
        "EXPIRADO": "OVERDUE",
        "CANCELADO": "CANCELLED",
        "FALHA": "FAILED",
        "ESTORNADO": "CANCELLED",
    }.get(transaction.status, "FAILED")
    return {
        "id": transaction.id,
        "credits": transaction.quantidade_creditos,
        "value": round((transaction.valor_centavos or package["price_cents"]) / 100, 2),
        "status": status,
        "pixQrCode": transaction.codigo_qr_pix,
        "pixCopyPaste": transaction.codigo_copia_cola_pix,
        "pixExpiresAt": transaction.pix_expira_em.isoformat() if transaction.pix_expira_em else None,
    }


def _asaas_request(method: str, path: str, **kwargs):
    if not ASAAS_BASE or not KEALEX_ASAAS_API_KEY:
        raise HTTPException(503, "Integração Asaas não configurada")
    try:
        response = httpx.request(method, f"{ASAAS_BASE}{path}", headers=ASAA_HEADERS, timeout=20, **kwargs)
    except httpx.TimeoutException as exc:
        raise HTTPException(504, "Timeout ao conectar com o Asaas") from exc
    except httpx.RequestError as exc:
        raise HTTPException(502, "Não foi possível conectar ao Asaas") from exc
    if response.status_code not in (200, 201):
        raise HTTPException(502, "O Asaas não conseguiu processar a solicitação")
    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(502, "Resposta inválida do Asaas") from exc


def _recover_payment(transaction: KeaCreditsTransaction) -> dict | None:
    response = _asaas_request("GET", "/payments", params={"externalReference": transaction.id, "limit": 10})
    data = response.get("data") or []
    return next((item for item in data if item.get("externalReference") == transaction.id), None)


def _fetch_pix(transaction: KeaCreditsTransaction, db: Session) -> None:
    if not transaction.asaas_pagamento_id or transaction.codigo_qr_pix and transaction.codigo_copia_cola_pix:
        return
    response = _asaas_request("GET", f"/payments/{transaction.asaas_pagamento_id}/pixQrCode")
    transaction.codigo_qr_pix = response.get("encodedImage")
    transaction.codigo_copia_cola_pix = response.get("payload")
    expires = response.get("expirationDate")
    if expires:
        try:
            transaction.pix_expira_em = datetime.fromisoformat(expires.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            transaction.pix_expira_em = None
    db.commit()
    db.refresh(transaction)


def create_recharge(db: Session, tenant_id: str, user_id: str, package_id: str, idempotency_key: str) -> dict:
    package = CREDIT_PACKAGES.get(package_id)
    if not package:
        raise HTTPException(422, "Pacote de KeaCredits inválido")
    if not idempotency_key or len(idempotency_key) > 100:
        raise HTTPException(422, "Informe uma chave de idempotência válida")
    if not ASAAS_BASE or not KEALEX_ASAAS_API_KEY:
        raise HTTPException(503, "Integração Asaas não configurada")

    tenant = db.query(Tenant).filter_by(id=tenant_id).first()
    if not tenant:
        raise HTTPException(404, "Organização não encontrada")
    if not tenant.asaas_customer_id:
        raise HTTPException(409, "Cadastre os dados de faturamento para gerar cobranças PIX")

    transaction = db.query(KeaCreditsTransaction).filter_by(
        organizacao_id=tenant_id, chave_idempotencia=idempotency_key,
    ).first()
    if transaction and transaction.pacote_id != package_id:
        raise HTTPException(409, "A chave de idempotência já foi usada em outro pacote")
    if transaction and transaction.status not in {"PENDENTE", "CONFIRMADO"}:
        raise HTTPException(409, "A recarga anterior não pode ser reutilizada. Gere uma nova solicitação.")
    created_transaction = transaction is None
    if created_transaction:
        transaction = KeaCreditsTransaction(
            id=str(uuid.uuid4()), organizacao_id=tenant_id, usuario_id=user_id,
            tipo="RECARGA", status="PENDENTE", quantidade_creditos=package["credits"],
            valor_centavos=package["price_cents"], chave_idempotencia=idempotency_key,
            pacote_id=package_id, descricao=f"Recarga KeaCredits {package['name']}",
            criado_em=datetime.utcnow(),
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)

    if not transaction.asaas_pagamento_id:
        if created_transaction:
            payment = _asaas_request("POST", "/payments", json={
                "customer": tenant.asaas_customer_id,
                "billingType": "PIX",
                "value": round(package["price_cents"] / 100, 2),
                "dueDate": date.today().isoformat(),
                "description": f"Recarga KeaCredits - {package['name']}",
                "externalReference": transaction.id,
            })
            transaction.asaas_pagamento_id = payment.get("id")
            if not transaction.asaas_pagamento_id:
                raise HTTPException(502, "O Asaas não retornou o identificador da cobrança")
        else:
            payment = _recover_payment(transaction)
            if not payment:
                raise HTTPException(409, "Estamos confirmando se o Asaas recebeu a cobrança. Aguarde e tente consultar novamente.")
            transaction.asaas_pagamento_id = payment.get("id")
        db.commit()
        db.refresh(transaction)

    _fetch_pix(transaction, db)
    return _pix_payload(transaction, package)


def recharge_status(db: Session, tenant_id: str, recharge_id: str) -> dict:
    transaction = db.query(KeaCreditsTransaction).filter_by(
        id=recharge_id, organizacao_id=tenant_id, tipo="RECARGA",
    ).first()
    if not transaction:
        raise HTTPException(404, "Recarga não encontrada")
    package = CREDIT_PACKAGES.get(transaction.pacote_id or "", {"price_cents": transaction.valor_centavos or 0})
    _fetch_pix(transaction, db)
    payload = _pix_payload(transaction, package)
    payload["saldoKeaCredits"] = wallet_balance(db, tenant_id)
    return payload


def apply_recharge_webhook(db: Session, event_name: str, payment: dict) -> bool:
    payment_id = payment.get("id")
    external_reference = payment.get("externalReference")
    query = db.query(KeaCreditsTransaction).filter(KeaCreditsTransaction.tipo == "RECARGA")
    transaction = query.filter_by(asaas_pagamento_id=payment_id).with_for_update().first() if payment_id else None
    if not transaction and external_reference:
        transaction = query.filter_by(id=external_reference).with_for_update().first()
    if not transaction:
        return False

    tenant = db.query(Tenant).filter_by(id=transaction.organizacao_id).first()
    if not tenant or payment.get("customer") != tenant.asaas_customer_id:
        raise HTTPException(409, "A cobrança recebida não corresponde à organização da recarga")
    if _centavos(payment.get("value")) != transaction.valor_centavos:
        raise HTTPException(409, "O valor recebido não corresponde ao pacote de créditos")
    if payment_id and transaction.asaas_pagamento_id not in (None, payment_id):
        raise HTTPException(409, "A cobrança recebida não corresponde à recarga")

    transaction.asaas_pagamento_id = payment_id or transaction.asaas_pagamento_id
    if event_name in PAID_EVENTS and transaction.status == "PENDENTE":
        wallet = _wallet(db, transaction.organizacao_id, lock=True)
        previous = wallet.saldo_creditos
        wallet.saldo_creditos += transaction.quantidade_creditos
        wallet.atualizado_em = datetime.utcnow()
        transaction.saldo_antes = previous
        transaction.saldo_depois = wallet.saldo_creditos
        transaction.status = "CONFIRMADO"
        transaction.confirmado_em = datetime.utcnow()
    elif event_name in REFUND_EVENTS and transaction.status == "CONFIRMADO":
        wallet = _wallet(db, transaction.organizacao_id, lock=True)
        previous = wallet.saldo_creditos
        wallet.saldo_creditos -= transaction.quantidade_creditos
        wallet.atualizado_em = datetime.utcnow()
        transaction.status = "ESTORNADO"
        transaction.confirmado_em = datetime.utcnow()
        reference = f"estorno-recarga:{transaction.id}"
        existing_refund = db.query(KeaCreditsTransaction).filter_by(
            organizacao_id=transaction.organizacao_id, chave_idempotencia=reference,
        ).first()
        if not existing_refund:
            db.add(KeaCreditsTransaction(
                id=str(uuid.uuid4()), organizacao_id=transaction.organizacao_id,
                usuario_id=transaction.usuario_id, tipo="ESTORNO", status="CONFIRMADO",
                quantidade_creditos=-transaction.quantidade_creditos,
                saldo_antes=previous, saldo_depois=wallet.saldo_creditos,
                chave_idempotencia=reference, pacote_id=transaction.pacote_id,
                descricao="Estorno de recarga Asaas", criado_em=datetime.utcnow(), confirmado_em=datetime.utcnow(),
            ))
    elif event_name in {"PAYMENT_OVERDUE", "PAYMENT_DELETED"} and transaction.status == "PENDENTE":
        transaction.status = "EXPIRADO" if event_name == "PAYMENT_OVERDUE" else "CANCELADO"
    db.flush()
    return True


def wallet_snapshot(db: Session, tenant_id: str) -> dict:
    return {"saldoKeaCredits": wallet_balance(db, tenant_id)}
