from pydantic import BaseModel

class CreditCardIn(BaseModel):
    holderName:  str
    number:      str
    expiryMonth: str
    expiryYear:  str
    ccv:         str

class HolderInfoIn(BaseModel):
    name:              str
    email:             str
    cpfCnpj:           str
    postalCode:        str
    addressNumber:     str
    addressComplement: str | None = None
    phone:             str | None = None
    mobilePhone:       str | None = None
    address:           str | None = None
    neighborhood:      str | None = None
    city:              str | None = None
    state:             str | None = None



class AssinarIn(BaseModel):
    plano:           str
    periodicidade:   str = "mensal"   # mensal | trimestral
    asaasCustomerId: str
    creditCard:      CreditCardIn
    holderInfo:      HolderInfoIn
    remoteIp:        str

class AssinarOut(BaseModel):
    subscriptionId: str
    plano:          str
    periodicidade:  str
    status:         str
    nextDueDate:    str
    value:          float
    valorMensal:    float
    desconto:       float

class AssinarPixIn(BaseModel):
    plano:           str
    periodicidade:   str = "mensal"
    asaasCustomerId: str

class AssinarPixOut(BaseModel):
    subscriptionId: str
    plano:          str
    periodicidade:  str
    status:         str
    nextDueDate:    str
    value:          float
    valorMensal:    float
    desconto:       float
    pixQrCode:      str   # base64 PNG do QR Code
    pixKey:         str   # payload copia-e-cola
    pixExpiresAt:   str   # ISO datetime de expiração
