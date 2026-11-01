from typing import Optional

from pydantic import BaseModel


class EscritorioIn(BaseModel):
    nome:     str
    cnpj:     Optional[str] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    email:    Optional[str] = None
    emailAcesso: Optional[str] = None
    senhaInicial: Optional[str] = None
    limiteAdvogados: int = 3

class EscritorioGetIn(BaseModel):
    id: str

class CriarAcessoIn(BaseModel):
    escritorioId: str
    emailAcesso: str
    senhaInicial: str

class EscritorioUpdate(BaseModel):
    id:       str
    nome:     Optional[str]  = None
    cnpj:     Optional[str]  = None
    endereco: Optional[str]  = None
    telefone: Optional[str]  = None
    email:    Optional[str]  = None
    ativo:    Optional[bool] = None
    limiteAdvogados: Optional[int] = None

class EscritorioDeleteIn(BaseModel):
    id: str

class MembroIn(BaseModel):
    usuarioId: str
    escritorioId: Optional[str] = None  # None = desassociar

class AssociarCodigoIn(BaseModel):
    codigo: str
