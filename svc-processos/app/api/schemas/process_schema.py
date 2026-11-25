from typing import Optional, List
from pydantic import BaseModel, Field
from app.domain.entities.process_status import StatusEnum

class ProcessoIn(BaseModel):
    numero:       str
    titulo:       str
    descricao:    str = ""
    clienteId:    str
    vara:         str = ""
    tribunal:     str = ""
    escritorioId: Optional[str] = None
    clientesVinculados: List[dict] = Field(default_factory=list)

class ProcessoGetIn(BaseModel):
    id: str

class ProcessoUpdate(BaseModel):
    id:        str
    numero:    Optional[str]        = None
    titulo:    Optional[str]        = None
    descricao: Optional[str]        = None
    status:    Optional[StatusEnum] = None
    vara:      Optional[str]        = None
    tribunal:  Optional[str]        = None

class ProcessoDeleteIn(BaseModel):
    id: str

class FaseIn(BaseModel):
    label: str
    ordem: int

class AvancarFaseIn(BaseModel):
    processoId: str
    faseAtual: int


class ProcessoClienteIn(BaseModel):
    clienteId: str
    proceduralRole: str = "Interessado"
    proceduralPole: Optional[str] = None
    isPrimary: bool = False
    notes: Optional[str] = None


class ProcessoClientesReplaceIn(BaseModel):
    clientes: List[ProcessoClienteIn]


class ProcessoClienteUpdate(BaseModel):
    proceduralRole: Optional[str] = None
    proceduralPole: Optional[str] = None
    isPrimary: Optional[bool] = None
    notes: Optional[str] = None


class ProcessoParteIn(BaseModel):
    name: str
    personType: str = "fisica"
    document: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    proceduralRole: str = "Interessado"
    isUnknown: bool = False


class ProcessoPartesReplaceIn(BaseModel):
    partes: List[ProcessoParteIn] = Field(default_factory=list)

