from typing import Optional
from pydantic import BaseModel, EmailStr

class ClienteIn(BaseModel):
    nome:        str
    email:       EmailStr
    telefone:    Optional[str] = None
    cpfCnpj:     Optional[str] = None
    endereco:    Optional[str] = None
    observacoes: Optional[str] = None

class ClienteUpdate(BaseModel):
    id:          str
    nome:        Optional[str]      = None
    email:       Optional[EmailStr] = None
    telefone:    Optional[str]      = None
    cpfCnpj:     Optional[str]      = None
    endereco:    Optional[str]      = None
    observacoes: Optional[str]      = None

class ClienteGetIn(BaseModel):
    id: str

class ClienteDeleteIn(BaseModel):
    id: str
