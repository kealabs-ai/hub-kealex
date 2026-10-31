from pydantic import BaseModel, EmailStr
from typing import Literal

class LoginIn(BaseModel):
    email: EmailStr
    senha: str

class RegisterIn(BaseModel):
    nome:     str
    email:    EmailStr
    cpfCnpj:  str
    whatsapp: str
    perfil:   Literal["advogado", "escritorio", "juridico", "corporativo"] = "advogado"
    senha:    str | None = None  # opcional; se omitida, gera senha temporária


class PreRegisterIn(BaseModel):
    nome:  str
    email: EmailStr
    senha: str

class PreRegisterOut(BaseModel):
    userId:   str
    tenantId: str
    token:    str  # token temporario para continuar o fluxo
