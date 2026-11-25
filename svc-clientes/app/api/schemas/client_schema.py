from typing import Optional
from pydantic import BaseModel, EmailStr

class ClienteIn(BaseModel):
    nome:        str
    email:       EmailStr
    telefone:    Optional[str] = None
    cpfCnpj:     Optional[str] = None
    cep:         Optional[str] = None
    endereco:    Optional[str] = None
    cidade:      Optional[str] = None
    estado:      Optional[str] = None
    rg: Optional[str] = None
    orgaoExpedidor: Optional[str] = None
    nacionalidade: Optional[str] = None
    estadoCivil: Optional[str] = None
    profissao: Optional[str] = None
    dataNascimento: Optional[str] = None
    razaoSocial: Optional[str] = None
    nomeFantasia: Optional[str] = None
    inscricaoEstadual: Optional[str] = None
    inscricaoMunicipal: Optional[str] = None
    representanteLegal: Optional[str] = None
    whatsapp: Optional[str] = None
    observacoes: Optional[str] = None

class ClienteUpdate(BaseModel):
    id:          str
    nome:        Optional[str]      = None
    email:       Optional[EmailStr] = None
    telefone:    Optional[str]      = None
    cpfCnpj:     Optional[str]      = None
    cep:         Optional[str]      = None
    endereco:    Optional[str]      = None
    cidade:      Optional[str]      = None
    estado:      Optional[str]      = None
    rg: Optional[str] = None
    orgaoExpedidor: Optional[str] = None
    nacionalidade: Optional[str] = None
    estadoCivil: Optional[str] = None
    profissao: Optional[str] = None
    dataNascimento: Optional[str] = None
    razaoSocial: Optional[str] = None
    nomeFantasia: Optional[str] = None
    inscricaoEstadual: Optional[str] = None
    inscricaoMunicipal: Optional[str] = None
    representanteLegal: Optional[str] = None
    whatsapp: Optional[str] = None
    observacoes: Optional[str]      = None

class ClienteGetIn(BaseModel):
    id: str

class ClienteDeleteIn(BaseModel):
    id: str
