from typing import Optional
from pydantic import BaseModel, EmailStr
from app.domain.entities.role import RoleEnum

class UsuarioIn(BaseModel):
    nome:         str
    email:        EmailStr
    senha:        str
    role:         RoleEnum
    escritorioId: Optional[str] = None
    oab: Optional[str] = None

class UsuarioListIn(BaseModel):
    role: Optional[RoleEnum] = None

class UsuarioGetIn(BaseModel):
    id: str

class UsuarioUpdate(BaseModel):
    id:           str
    nome:         Optional[str]      = None
    email:        Optional[EmailStr] = None
    senha:        Optional[str]      = None
    role:         Optional[RoleEnum] = None
    ativo:        Optional[bool]     = None
    escritorioId: Optional[str]      = None
    clearEscritorio: bool            = False  # True = desassociar escritório

    oab: Optional[str] = None

class UsuarioDeleteIn(BaseModel):
    id: str

class ChavePublicaIn(BaseModel):
    orgao: str
    chavePublica: str

class ConsultaDataJudIn(BaseModel):
    tribunal: str
    numeroProcesso: str

class ModalidadeIn(BaseModel):
    usuarioId: str
    escritorioId: Optional[str] = None  # None = autônomo
