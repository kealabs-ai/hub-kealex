from typing import Optional
from pydantic import BaseModel
from app.domain.entities.process_status import StatusEnum

class ProcessoIn(BaseModel):
    numero:       str
    titulo:       str
    descricao:    str = ""
    clienteId:    str
    vara:         str = ""
    tribunal:     str = ""
    escritorioId: Optional[str] = None

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

