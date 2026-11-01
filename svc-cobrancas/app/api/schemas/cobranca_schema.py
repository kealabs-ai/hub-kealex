from typing import Optional

from pydantic import BaseModel


class CobrancaIn(BaseModel):
    processoId: str
    clienteId: str
    valorCentavos: int
    dataVencimento: Optional[str] = None


class CreditCardIn(BaseModel):
    holderName: str
    number: str
    expiryMonth: str
    expiryYear: str
    ccv: str


class CreditCardHolderInfoIn(BaseModel):
    name: str
    email: str
    cpfCnpj: str
    postalCode: str
    addressNumber: str
    addressComplement: Optional[str] = None
    phone: str


class PagamentoIn(BaseModel):
    cobrancaId: str
    customer: str
    billingType: str
    description: Optional[str] = None
    creditCardToken: Optional[str] = None
    creditCard: Optional[CreditCardIn] = None
    creditCardHolderInfo: Optional[CreditCardHolderInfoIn] = None
