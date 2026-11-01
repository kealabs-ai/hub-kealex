from typing import Optional
from pydantic import BaseModel
from app.domain.entities.prazo_status import StatusEnum

class PrazoIn(BaseModel):
    processoId:     str
    titulo:         str
    descricao:      str = ""
    dataVencimento: str
    escritorioId:   Optional[str] = None

class PrazoGetIn(BaseModel):
    id: str

class PrazoByProcessoIn(BaseModel):
    processoId: str

class PrazoVencendoIn(BaseModel):
    dias: int = 7

class PrazoUpdate(BaseModel):
    id:             str
    titulo:         Optional[str]        = None
    descricao:      Optional[str]        = None
    dataVencimento: Optional[str]        = None
    status:         Optional[StatusEnum] = None

class PrazoDeleteIn(BaseModel):
    id: str

